"""
Price forecast for the next 4 weeks.

One GradientBoostingRegressor per horizon (7, 14, 21, 28 days) predicts the
log-change of the modal price from today's features:
  - recent price level, lags (7/14/28 days) and rolling means
  - seasonality (day-of-year of the target date)
  - 30-day rainfall and temperature (when weather history is available)

The model is backtested on the last 20% of the data and compared with a
linear-trend baseline, so the accuracy claim is measured, not assumed.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

HORIZONS = (7, 14, 21, 28)
MIN_DAYS_FOR_MODEL = 90
STORAGE_COST_PER_WEEK = 0.005      # 0.5% of the price per week of waiting


def daily_series(rows):
    """[{'date', 'price'}] -> continuous daily Series (forward filled)."""

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    series = (
        df.groupby("date")["price"].mean().sort_index().asfreq("D")
    )

    return series.interpolate(limit_direction="both")


def _features(prices, weather, index, horizon):
    """Feature frame for every day in `index` (target = index + horizon)."""

    frame = pd.DataFrame(index=index)

    frame["price"] = prices.loc[index]

    for lag in (7, 14, 28):
        frame[f"lag_{lag}"] = prices.shift(lag).loc[index] / frame["price"]

    frame["mean_14"] = prices.rolling(14).mean().loc[index] / frame["price"]
    frame["mean_28"] = prices.rolling(28).mean().loc[index] / frame["price"]

    target_day = (index + pd.Timedelta(days=horizon)).dayofyear
    frame["season_sin"] = np.sin(2 * np.pi * target_day / 365.25)
    frame["season_cos"] = np.cos(2 * np.pi * target_day / 365.25)

    if weather is not None:
        rain = weather["rain"].reindex(prices.index).rolling(30, min_periods=10).sum()
        temp = weather["temp"].reindex(prices.index).rolling(30, min_periods=10).mean()

        frame["rain_30"] = rain.loc[index].values
        frame["temp_30"] = temp.loc[index].values

    return frame.drop(columns=["price"])


def _training_set(prices, weather, horizon):
    index = prices.index[28:-horizon]

    X = _features(prices, weather, index, horizon)

    # Log-change keeps the model independent of the price level
    y = np.log(prices.shift(-horizon).loc[index] / prices.loc[index])

    valid = X.notna().all(axis=1) & y.notna()

    return X[valid], y[valid]


def _new_model():
    return GradientBoostingRegressor(
        n_estimators=150,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        random_state=0
    )


def _linear_prediction(prices, day, horizon, window=60):
    """Baseline: fit a straight line to the previous `window` days."""

    history = prices.loc[:day].iloc[-window:]
    x = np.arange(len(history))

    slope, intercept = np.polyfit(x, history.values, 1)

    return max(slope * (len(history) - 1 + horizon) + intercept, 1.0)


def _linear_forecast(prices):
    """Fallback for short histories: straight-line trend, wide bands."""

    last = prices.index[-1]
    current = float(prices.iloc[-1])
    spread = float(prices.pct_change().std() or 0.03)

    forecast = []

    for horizon in HORIZONS:
        price = _linear_prediction(prices, last, horizon, window=min(60, len(prices)))
        band = current * spread * np.sqrt(horizon)

        forecast.append({
            "days": horizon,
            "date": (last + pd.Timedelta(days=horizon)).strftime("%Y-%m-%d"),
            "price": round(float(price), 2),
            "low": round(float(max(price - band, 0)), 2),
            "high": round(float(price + band), 2),
        })

    return forecast, {"model": "linear-trend", "reason": "not enough history"}


def forecast_prices(rows, weather=None):
    """
    rows:    [{'date', 'price'}] price history (oldest first)
    weather: DataFrame(date index; rain, temp) or None

    Returns (forecast, metrics, features_used).
    """

    prices = daily_series(rows)
    prices = prices[prices > 0]
    prices = prices.asfreq("D").interpolate(limit_direction="both")

    features_used = ["price history", "seasonality"]

    if len(prices) < MIN_DAYS_FOR_MODEL:
        forecast, metrics = _linear_forecast(prices)
        metrics["history_days"] = len(prices)

        return forecast, metrics, ["price history"]

    if weather is not None and len(weather) > 60:
        features_used.append("rainfall and temperature")
    else:
        weather = None

    forecast = []
    per_horizon_metrics = {}
    last_day = prices.index[-1]

    for horizon in HORIZONS:
        X, y = _training_set(prices, weather, horizon)

        if len(X) < 60:
            return (*_linear_forecast(prices), ["price history"])

        # --- backtest: train on the first 80%, test on the last 20% ---
        split = int(len(X) * 0.8)
        model = _new_model().fit(X.iloc[:split], y.iloc[:split])

        test_X, test_y = X.iloc[split:], y.iloc[split:]
        predicted_log = model.predict(test_X)

        actual = prices.loc[test_X.index] * np.exp(test_y.values)
        predicted = prices.loc[test_X.index] * np.exp(predicted_log)

        linear = np.array([
            _linear_prediction(prices, day, horizon) for day in test_X.index
        ])

        mae_model = float(np.mean(np.abs(actual - predicted)))
        mae_linear = float(np.mean(np.abs(actual - linear)))
        mape = float(np.mean(np.abs(actual - predicted) / actual) * 100)

        residuals = test_y.values - predicted_log
        low_q, high_q = np.quantile(residuals, [0.1, 0.9])

        per_horizon_metrics[horizon] = {
            "mae": round(mae_model, 2),
            "mape_percent": round(mape, 2),
            "linear_baseline_mae": round(mae_linear, 2),
        }

        # --- final model on all data, predict from today ---
        model = _new_model().fit(X, y)

        today = _features(prices, weather, prices.index[-1:], horizon)

        if today.isna().any(axis=None):
            today = today.fillna(X.median())

        log_change = float(model.predict(today)[0])
        current = float(prices.iloc[-1])

        price = current * np.exp(log_change)

        forecast.append({
            "days": horizon,
            "date": (last_day + pd.Timedelta(days=horizon)).strftime("%Y-%m-%d"),
            "price": round(float(price), 2),
            "low": round(float(current * np.exp(log_change + low_q)), 2),
            "high": round(float(current * np.exp(log_change + high_q)), 2),
        })

    maes = [m["mae"] for m in per_horizon_metrics.values()]
    linear_maes = [m["linear_baseline_mae"] for m in per_horizon_metrics.values()]

    metrics = {
        "model": "gradient-boosting",
        "history_days": len(prices),
        "history_years": round(len(prices) / 365.25, 1),
        "mae": round(float(np.mean(maes)), 2),
        "linear_baseline_mae": round(float(np.mean(linear_maes)), 2),
        "beats_linear_baseline": bool(np.mean(maes) < np.mean(linear_maes)),
        "per_horizon": per_horizon_metrics,
    }

    return forecast, metrics, features_used


def best_time_to_sell(forecast, current_price):
    """Highest expected price after subtracting a small waiting cost."""

    best = {"days": 0, "price": current_price, "net": current_price}

    for point in forecast:
        weeks = point["days"] / 7
        net = point["price"] - current_price * STORAGE_COST_PER_WEEK * weeks

        if net > best["net"]:
            best = {"days": point["days"], "price": point["price"], "net": net}

    if best["days"] == 0:
        return {
            "action": "sell_now",
            "days": 0,
            "expected_price": round(float(current_price), 2),
            "message": "Prices are expected to fall or stay flat. Sell now."
        }

    gain = (best["price"] - current_price) / current_price * 100

    return {
        "action": "wait",
        "days": best["days"],
        "expected_price": round(float(best["price"]), 2),
        "message": (
            f"Best expected price in about {best['days']} days "
            f"(around Rs {best['price']:.0f}, {gain:+.1f}% vs now)."
        )
    }
