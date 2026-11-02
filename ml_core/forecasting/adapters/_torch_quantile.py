"""Entrenamiento cuantílico compacto en CPU (LSTM / TFT-lite / PatchTST-lite)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

from ml_core.forecasting.adapters._common import (
    dump_json,
    last_y,
    load_json,
    lookback_matrix,
    prediction_rows,
    residual_scale,
    series_by_id,
    train_values,
)
from ml_core.forecasting.dataset import horizon_steps
from ml_core.forecasting.problem import ProblemSpec

DEVICE = torch.device("cpu")


class QuantileHead(nn.Module):
    def __init__(self, hidden: int) -> None:
        super().__init__()
        self.net = nn.Linear(hidden, 4)

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        return self.net(h)


class LSTMNet(nn.Module):
    def __init__(self, hidden: int = 16) -> None:
        super().__init__()
        self.rnn = nn.LSTM(1, hidden, batch_first=True)
        self.head = QuantileHead(hidden)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.rnn(x)
        return self.head(out[:, -1, :])


class PatchNet(nn.Module):
    def __init__(self, lookback: int, hidden: int = 16, heads: int = 2) -> None:
        super().__init__()
        self.proj = nn.Linear(1, hidden)
        self.attn = nn.MultiheadAttention(hidden, heads, batch_first=True)
        self.head = QuantileHead(hidden)
        self.lookback = lookback

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.proj(x)
        a, _ = self.attn(h, h, h, need_weights=False)
        return self.head(a.mean(dim=1))


class MixerNet(nn.Module):
    """TTM-like: mezcla parches temporales con MLP (muy pequeño)."""

    def __init__(self, lookback: int, hidden: int = 16) -> None:
        super().__init__()
        self.fc1 = nn.Linear(lookback, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.head = QuantileHead(hidden)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = torch.relu(self.fc1(x.squeeze(-1)))
        z = torch.relu(self.fc2(z))
        return self.head(z)


class GRNLSTM(nn.Module):
    """TFT-lite: puerta de selección de la ventana + LSTM."""

    def __init__(self, hidden: int = 16) -> None:
        super().__init__()
        self.gate = nn.Linear(1, 1)
        self.rnn = nn.LSTM(1, hidden, batch_first=True)
        self.head = QuantileHead(hidden)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        g = torch.sigmoid(self.gate(x))
        out, _ = self.rnn(x * g)
        return self.head(out[:, -1, :])


def pinball_batch(pred: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    taus = pred.new_tensor([0.10, 0.50, 0.90, 0.95]).view(1, 4)
    err = y.unsqueeze(1) - pred
    return torch.mean(torch.maximum(taus * err, (taus - 1) * err))


def train_net(
    net: nn.Module,
    X: np.ndarray,
    y: np.ndarray,
    *,
    epochs: int = 12,
    lr: float = 1e-2,
) -> nn.Module:
    if len(X) == 0:
        return net
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    xt = torch.tensor(X, dtype=torch.float32).unsqueeze(-1)
    yt = torch.tensor(y, dtype=torch.float32)
    net.train()
    for _ in range(epochs):
        opt.zero_grad()
        pred = net(xt)
        loss = pinball_batch(pred, yt)
        loss.backward()
        opt.step()
    net.eval()
    return net


class TorchQuantileAdapter:
    family = "transformer"
    backend = "torch-lite"
    net_kind = "lstm"
    name = "lstm"

    def __init__(self, *, epochs: int = 12, hidden: int = 16) -> None:
        self.epochs = epochs
        self.hidden = hidden
        self.lookback = 8
        self.spreads = residual_scale(np.array([0.0, 0.1]))
        self.net: nn.Module | None = None
        self.k_step = 1

    def _build(self, lookback: int) -> nn.Module:
        kind = self.net_kind
        if kind == "patch":
            return PatchNet(lookback, self.hidden)
        if kind == "tft":
            return GRNLSTM(self.hidden)
        if kind == "mixer":
            return MixerNet(lookback, self.hidden)
        return LSTMNet(self.hidden)

    def fit(self, train: pd.DataFrame, spec: ProblemSpec) -> None:
        y = train_values(train)
        self.spreads = residual_scale(y)
        self.lookback = min(int(spec.lookback), max(4, y.size // 3), 32)
        steps = horizon_steps(spec)
        self.k_step = int(steps[0]) if steps else 1
        X, yt = lookback_matrix(y, self.lookback, self.k_step)
        self.net = self._build(self.lookback)
        if len(X) >= 4:
            self.net = train_net(self.net, X, yt, epochs=self.epochs)

    def predict_quantiles(self, context: pd.DataFrame, spec: ProblemSpec) -> pd.DataFrame:
        groups = series_by_id(context)
        net = self.net
        lookback = self.lookback

        def yhat(g: pd.DataFrame, _spec: ProblemSpec) -> float:
            arr = pd.to_numeric(g["y"], errors="coerce").dropna().to_numpy(dtype=float)
            if net is None or arr.size < lookback:
                return last_y(g)
            x = torch.tensor(arr[-lookback:], dtype=torch.float32).view(1, lookback, 1)
            with torch.no_grad():
                q = net(x).cpu().numpy()[0]
            return float(q[1])

        return prediction_rows(groups, spec, yhat, self.spreads)

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        dump_json(
            path.with_suffix(".json"),
            {
                "name": self.name,
                "kind": self.net_kind,
                "lookback": self.lookback,
                "hidden": self.hidden,
                "k_step": self.k_step,
                "spreads": self.spreads,
                "family": self.family,
            },
        )
        if self.net is not None:
            torch.save(self.net.state_dict(), path)

    @classmethod
    def load(cls, path: Path) -> "TorchQuantileAdapter":
        path = Path(path)
        meta = load_json(path.with_suffix(".json"))
        obj = cls()
        obj.name = meta["name"]
        obj.net_kind = meta["kind"]
        obj.lookback = int(meta["lookback"])
        obj.hidden = int(meta["hidden"])
        obj.k_step = int(meta.get("k_step", 1))
        obj.spreads = {k: float(v) for k, v in meta["spreads"].items()}
        obj.family = meta.get("family", obj.family)
        obj.net = obj._build(obj.lookback)
        if path.exists():
            obj.net.load_state_dict(torch.load(path, map_location="cpu"))
            obj.net.eval()
        return obj
