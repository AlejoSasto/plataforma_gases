"""Arquitecturas PyTorch para series temporales."""

from __future__ import annotations

import torch
import torch.nn as nn


class SequenceMultiHead(nn.Module):
    """Encoder secuencial + cabezas de clasificación y/o regresión."""

    def __init__(
        self,
        *,
        encoder: nn.Module,
        hidden: int,
        task: str = "both",
    ):
        super().__init__()
        self.encoder = encoder
        self.task = task
        self.cls_head = nn.Linear(hidden, 1) if task in ("classification", "both") else None
        self.reg_head = nn.Linear(hidden, 1) if task in ("regression", "both") else None

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        # x: [B, T, F]
        h = self.encoder(x)
        out: dict[str, torch.Tensor] = {"embedding": h}
        if self.cls_head is not None:
            out["logits"] = self.cls_head(h).squeeze(-1)
        if self.reg_head is not None:
            out["reg"] = self.reg_head(h).squeeze(-1)
        return out


class _LSTMEncoder(nn.Module):
    def __init__(self, n_features: int, hidden: int = 64, layers: int = 1):
        super().__init__()
        self.rnn = nn.LSTM(n_features, hidden, num_layers=layers, batch_first=True)

    def forward(self, x):
        out, _ = self.rnn(x)
        return out[:, -1, :]


class _GRUEncoder(nn.Module):
    def __init__(self, n_features: int, hidden: int = 64, layers: int = 1):
        super().__init__()
        self.rnn = nn.GRU(n_features, hidden, num_layers=layers, batch_first=True)

    def forward(self, x):
        out, _ = self.rnn(x)
        return out[:, -1, :]


class _TransformerEncoder(nn.Module):
    def __init__(self, n_features: int, hidden: int = 64, nhead: int = 4, layers: int = 2):
        super().__init__()
        self.proj = nn.Linear(n_features, hidden)
        layer = nn.TransformerEncoderLayer(
            d_model=hidden, nhead=nhead, batch_first=True, dim_feedforward=hidden * 2
        )
        self.enc = nn.TransformerEncoder(layer, num_layers=layers)

    def forward(self, x):
        h = self.proj(x)
        h = self.enc(h)
        return h.mean(dim=1)


class _CNN1DEncoder(nn.Module):
    def __init__(self, n_features: int, hidden: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(n_features, hidden, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv1d(hidden, hidden, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
        )

    def forward(self, x):
        # x [B,T,F] -> [B,F,T]
        z = x.transpose(1, 2)
        z = self.net(z).squeeze(-1)
        return z


def build_sequence_model(
    algorithm: str,
    *,
    n_features: int,
    task: str = "both",
    hidden: int = 64,
) -> SequenceMultiHead:
    algo = algorithm.lower()
    if algo == "lstm":
        enc = _LSTMEncoder(n_features, hidden=hidden)
    elif algo == "gru":
        enc = _GRUEncoder(n_features, hidden=hidden)
    elif algo == "transformer":
        # nhead must divide hidden
        h = hidden if hidden % 4 == 0 else 64
        enc = _TransformerEncoder(n_features, hidden=h, nhead=4)
        hidden = h
    elif algo == "cnn1d":
        enc = _CNN1DEncoder(n_features, hidden=hidden)
    else:
        raise ValueError(f"Arquitectura secuencial desconocida: {algorithm}")
    return SequenceMultiHead(encoder=enc, hidden=hidden, task=task)
