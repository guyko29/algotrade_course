"""Train and evaluate supervised return-forecasting models.

Predicts the next ``horizon``-day log return from the technical-indicator matrix
built in :mod:`portfolio.analytics.features`. Validation is strictly time-ordered
(expanding-window walk-forward) — rows are never shuffled — so reported metrics
contain no look-ahead leakage.

Every heavy dependency (scikit-learn, xgboost) is imported lazily and guarded, so
the surrounding app degrades gracefully to a historical-mean fallback when the ML
stack is unavailable or training cannot proceed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from portfolio.analytics.features import TARGET_COLUMN, feature_columns
from portfolio.analytics.models import MlForecastResult
from portfolio.logger import get_logger

logger = get_logger(__name__)

_MODEL_LABELS = {
    "xgboost": "XGBoost",
    "ridge": "Ridge",
    "linear": "Linear Regression",
    "random_forest": "Random Forest",
}


def _build_estimator(model_type: str):
    """Return an unfitted estimator, or ``None`` if its library is unavailable."""
    model_type = model_type.lower()

    if model_type == "xgboost":
        try:
            from xgboost import XGBRegressor
        except ImportError:
            logger.warning("xgboost not installed; cannot build XGBoost model")
            return None
        return XGBRegressor(
            n_estimators=200,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=1,
        )

    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.linear_model import LinearRegression, Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        logger.warning("scikit-learn not installed; cannot build %s model", model_type)
        return None

    if model_type == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    if model_type == "linear":
        return make_pipeline(StandardScaler(), LinearRegression())
    if model_type == "random_forest":
        return RandomForestRegressor(
            n_estimators=200, max_depth=5, random_state=42, n_jobs=1
        )

    logger.warning("Unknown ML_MODEL '%s'; no estimator built", model_type)
    return None


def _walk_forward_metrics(estimator, x: np.ndarray, y: np.ndarray) -> tuple[float | None, float | None, float | None]:
    """Expanding-window walk-forward MAE / RMSE / R² (no row shuffling)."""
    try:
        from sklearn.base import clone
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.model_selection import TimeSeriesSplit
    except ImportError:
        return None, None, None

    n_splits = min(5, max(2, len(y) // 100))
    if len(y) <= n_splits + 1:
        return None, None, None

    splitter = TimeSeriesSplit(n_splits=n_splits)
    preds: list[np.ndarray] = []
    actuals: list[np.ndarray] = []
    for train_idx, test_idx in splitter.split(x):
        model = clone(estimator)
        model.fit(x[train_idx], y[train_idx])
        preds.append(model.predict(x[test_idx]))
        actuals.append(y[test_idx])

    y_pred = np.concatenate(preds)
    y_true = np.concatenate(actuals)
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 else None
    return mae, rmse, r2


def _feature_importance(estimator, columns: list[str]) -> list[tuple[str, float]]:
    """Extract normalized feature importances (tree gain or |coef|)."""
    model = estimator
    # Unwrap sklearn pipelines (scaler + estimator).
    if hasattr(model, "steps"):
        model = model.steps[-1][1]

    importances: np.ndarray | None = None
    if hasattr(model, "feature_importances_"):
        importances = np.asarray(model.feature_importances_, dtype=float)
    elif hasattr(model, "coef_"):
        importances = np.abs(np.asarray(model.coef_, dtype=float)).ravel()

    if importances is None or importances.size != len(columns):
        return []

    total = importances.sum()
    if total > 0:
        importances = importances / total
    ranked = sorted(zip(columns, importances.tolist()), key=lambda item: item[1], reverse=True)
    return ranked


def train_return_model(
    matrix: pd.DataFrame,
    model_type: str,
    min_train_rows: int,
) -> MlForecastResult:
    """Train on the full matrix and predict the next-horizon return for the latest row.

    Returns an :class:`MlForecastResult`. On any failure (too few rows, missing
    library, fit error) ``trained`` is ``False`` and ``predicted_daily_return`` is
    ``nan`` — callers fall back to the historical mean.
    """
    label = _MODEL_LABELS.get(model_type.lower(), model_type)

    def _empty(reason: str, n_rows: int) -> MlForecastResult:
        logger.info("ML forecast unavailable (%s): %s", label, reason)
        return MlForecastResult(
            model_name=f"{label} (fallback: {reason})",
            trained=False,
            n_train_rows=n_rows,
            cv_mae=None,
            cv_rmse=None,
            cv_r2=None,
            predicted_horizon_return=float("nan"),
            feature_importance=[],
        )

    if matrix.empty:
        return _empty("no features", 0)

    columns = feature_columns(matrix)
    n_rows = len(matrix)
    if n_rows < min_train_rows:
        return _empty(f"{n_rows} rows < {min_train_rows} min", n_rows)

    estimator = _build_estimator(model_type)
    if estimator is None:
        return _empty("library unavailable", n_rows)

    x = matrix[columns].to_numpy(dtype=float)
    y = matrix[TARGET_COLUMN].to_numpy(dtype=float)

    try:
        mae, rmse, r2 = _walk_forward_metrics(estimator, x, y)
        estimator.fit(x, y)
        latest = matrix[columns].iloc[[-1]].to_numpy(dtype=float)
        predicted_horizon = float(estimator.predict(latest)[0])
        importance = _feature_importance(estimator, columns)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully on any model error
        logger.warning("ML training failed for %s: %s", label, exc)
        return _empty("training error", n_rows)

    logger.info(
        "ML forecast %s trained on %d rows | horizon-return=%.5f | CV MAE=%s R2=%s",
        label,
        n_rows,
        predicted_horizon,
        f"{mae:.5f}" if mae is not None else "n/a",
        f"{r2:.3f}" if r2 is not None else "n/a",
    )

    return MlForecastResult(
        model_name=label,
        trained=True,
        n_train_rows=n_rows,
        cv_mae=mae,
        cv_rmse=rmse,
        cv_r2=r2,
        predicted_horizon_return=predicted_horizon,
        feature_importance=importance,
    )
