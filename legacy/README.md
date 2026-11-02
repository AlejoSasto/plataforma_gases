# Legado retirado

## Plan 15 F1
- `ml_core_augmentation.py` — clonado 24m

## Plan 23 F5
- `ml_core_models/` — zoo sklearn/XGBoost/LSTM/GRU/Transformer vanilla
- `ml_core_features/` — `build_features`, `targets`, `sequences` (etiqueta `evento_final`, p95 global)
- `scripts/` — `train_full_model_zoo.py`, `retrain_*`

**No importar** desde `app/` ni `ml_core/forecasting`. El Laboratorio usa solo `ml_core.forecasting.adapters`.
