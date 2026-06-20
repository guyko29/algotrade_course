"""STL + GARCH price forecasting."""

from __future__ import annotations

import numpy as np
import pandas as pd
from arch import arch_model
from statsmodels.tsa.seasonal import STL

from portfolio.analytics.models import PriceForecastResult
from portfolio.logger import get_logger

logger = get_logger(__name__)


def forecast_price_stl_garch(prices: pd.Series, horizon: int = 21) -> PriceForecastResult | None:
    if len(prices) < 120:
        logger.info("Skipping forecast: only %s observations available", len(prices))
        return None

    log_prices = np.log(prices.astype(float))
    seasonal_period = 5
    stl_fit = STL(log_prices, period=seasonal_period, robust=True).fit()
    residuals = stl_fit.resid.dropna()
    if len(residuals) < 60:
        return None

    try:
        garch = arch_model(residuals * 100, vol="Garch", p=1, q=1, rescale=False)
        garch_fit = garch.fit(disp="off", show_warning=False)
        garch_forecast = garch_fit.forecast(horizon=horizon)
        forecast_vol = np.sqrt(garch_forecast.variance.values[-1]) / 100.0
    except Exception as exc:
        logger.warning("GARCH fit failed, using residual std: %s", exc)
        forecast_vol = np.full(horizon, float(residuals.std(ddof=1)))

    last_trend = stl_fit.trend.dropna()
    lookback = min(21, len(last_trend))
    trend_slope = float(last_trend.iloc[-1] - last_trend.iloc[-lookback]) / lookback
    seasonal_tail = stl_fit.seasonal.dropna().values[-seasonal_period:]

    future_dates = pd.bdate_range(prices.index[-1], periods=horizon + 1)[1:]
    median_path, lower_path, upper_path, trend_path = [], [], [], []

    for step in range(horizon):
        trend_value = float(last_trend.iloc[-1] + trend_slope * (step + 1))
        seasonal_value = float(seasonal_tail[step % seasonal_period])
        drift = trend_value + seasonal_value
        shock = 1.28 * float(forecast_vol[step]) if step < len(forecast_vol) else 1.28 * float(residuals.std(ddof=1))

        trend_path.append(trend_value)
        median_path.append(float(np.exp(drift)))
        lower_path.append(float(np.exp(drift - shock)))
        upper_path.append(float(np.exp(drift + shock)))

    history_tail = prices.tail(90)
    return PriceForecastResult(
        dates=[date.strftime("%Y-%m-%d") for date in future_dates],
        history_dates=[date.strftime("%Y-%m-%d") for date in history_tail.index],
        history_prices=history_tail.tolist(),
        forecast_median=median_path,
        forecast_lower=lower_path,
        forecast_upper=upper_path,
        trend_component=[float(np.exp(value)) for value in trend_path],
    )
