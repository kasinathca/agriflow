from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd

from agriflow.data.identity import make_market_id

MARKETS = [
    ("Maharashtra", "Nashik", "Lasalgaon", 20.1472, 74.2401),
    ("Maharashtra", "Pune", "Pune", 18.5204, 73.8567),
    ("Maharashtra", "Mumbai", "Vashi", 19.0760, 72.9980),
    ("Madhya Pradesh", "Indore", "Indore", 22.7196, 75.8577),
    ("Madhya Pradesh", "Ujjain", "Ujjain", 23.1765, 75.7885),
    ("Delhi", "Delhi", "Azadpur", 28.7041, 77.1025),
    ("Uttar Pradesh", "Agra", "Agra", 27.1767, 78.0081),
    ("Uttar Pradesh", "Kanpur Nagar", "Kanpur", 26.4499, 80.3319),
    ("Karnataka", "Kolar", "Kolar", 13.1362, 78.1291),
    ("Karnataka", "Bengaluru Urban", "Bengaluru", 12.9716, 77.5946),
    ("Tamil Nadu", "Chennai", "Koyambedu", 13.0694, 80.1948),
    ("Tamil Nadu", "Coimbatore", "Coimbatore", 11.0168, 76.9558),
    ("Kerala", "Ernakulam", "Ernakulam", 9.9816, 76.2999),
    ("Kerala", "Thiruvananthapuram", "Thiruvananthapuram", 8.5241, 76.9366),
    ("Rajasthan", "Jaipur", "Jaipur", 26.9124, 75.7873),
    ("Rajasthan", "Kota", "Kota", 25.2138, 75.8648),
]

COMMODITIES = {
    "Onion": {"base": 2200, "leader": "Lasalgaon", "weather_sens": 0.22, "arrival_base": 580},
    "Tomato": {"base": 1800, "leader": "Kolar", "weather_sens": 0.32, "arrival_base": 430},
    "Potato": {"base": 1550, "leader": "Agra", "weather_sens": 0.15, "arrival_base": 510},
    "Wheat": {"base": 2450, "leader": "Indore", "weather_sens": 0.08, "arrival_base": 700},
    "Rice": {"base": 3100, "leader": "Koyambedu", "weather_sens": 0.10, "arrival_base": 650},
}

STATE_FACTOR = {
    "Maharashtra": 1.00,
    "Madhya Pradesh": 0.96,
    "Delhi": 1.15,
    "Uttar Pradesh": 0.98,
    "Karnataka": 1.03,
    "Tamil Nadu": 1.08,
    "Kerala": 1.18,
    "Rajasthan": 1.01,
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def generate_demo(output_dir: Path, seed: int = 240124) -> tuple[Path, Path, Path]:
    """Generate deterministic, clearly synthetic data for zero-credential demonstration."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", "2025-12-31", freq="D")

    market_df = pd.DataFrame(MARKETS, columns=["state", "district", "market", "lat", "lon"])
    market_df["market_id"] = [make_market_id(s,d,m) for s,d,m in zip(market_df.state, market_df.district, market_df.market)]
    market_df["coordinate_quality"] = "demo_known"

    weather_rows: list[dict] = []
    weather_cache: dict[tuple[str, pd.Timestamp], tuple[float, float]] = {}
    for _, m in market_df.iterrows():
        lat = float(m.lat)
        # seasonal temperature; southern locations have weaker amplitude
        amp = 7 + 0.15 * max(lat - 10, 0)
        for i, d in enumerate(dates):
            doy = d.dayofyear
            temp = 25 + amp * math.sin(2 * math.pi * (doy - 95) / 365.25) + rng.normal(0, 1.8)
            monsoon = math.exp(-0.5 * ((doy - 210) / 55) ** 2)
            rain_prob = min(0.65, 0.05 + 0.50 * monsoon + (0.12 if m.state in {"Kerala", "Karnataka"} else 0))
            rain = float(rng.gamma(2.0, 7.0)) if rng.random() < rain_prob else 0.0
            # deterministic severe weather windows to make event-study/ripple views testable
            if m.state == "Maharashtra" and pd.Timestamp("2024-09-05") <= d <= pd.Timestamp("2024-09-12"):
                rain += 55 + rng.gamma(2, 8)
            if m.state == "Karnataka" and pd.Timestamp("2025-05-10") <= d <= pd.Timestamp("2025-05-16"):
                temp += 6
                rain *= 0.2
            weather_cache[(m.market, d)] = (rain, temp)
            weather_rows.append({
                "date": d.date().isoformat(), "state": m.state, "district": m.district,
                "market": m.market, "market_id": m.market_id, "lat": m.lat, "lon": m.lon,
                "rainfall_mm": round(rain, 2), "temperature_c": round(temp, 2),
                "source": "AGRIFLOW_DEMO_SYNTHETIC", "data_mode": "DEMO"
            })

    price_rows: list[dict] = []
    n = len(dates)
    for commodity, spec in COMMODITIES.items():
        leader_row = market_df.loc[market_df.market.eq(spec["leader"])].iloc[0]
        leader_lat, leader_lon = float(leader_row.lat), float(leader_row.lon)
        # Commodity-specific leader return process. Followers receive delayed, attenuated
        # versions plus local noise; this makes the demo a known-answer visual fixture.
        leader_ret = np.zeros(n)
        innovations = rng.normal(0, 0.010 if commodity in {"Wheat", "Rice"} else 0.016, n)
        for t in range(1, n):
            leader_ret[t] = 0.45 * leader_ret[t - 1] + innovations[t]
        # Short, interpretable commodity shocks (not empirical events).
        if commodity == "Onion":
            for ds, bump in [("2024-09-08", .12), ("2024-09-09", .08), ("2024-09-10", .05)]:
                leader_ret[np.where(dates == pd.Timestamp(ds))[0][0]] += bump
        if commodity == "Tomato":
            for ds, bump in [("2025-05-14", .10), ("2025-05-15", .07), ("2025-05-16", .04)]:
                leader_ret[np.where(dates == pd.Timestamp(ds))[0][0]] += bump

        for _, m in market_df.iterrows():
            dist = _haversine(leader_lat, leader_lon, float(m.lat), float(m.lon))
            lag = 0 if m.market == spec["leader"] else int(np.clip(1 + round(dist / 650), 1, 5))
            transmission = max(0.45, 0.94 - dist / 4200)
            shifted = np.roll(leader_ret, lag) * transmission
            if lag:
                shifted[:lag] = 0.0
            idio_sd = 0.006 if commodity in {"Wheat", "Rice"} else 0.008
            market_ret = shifted + rng.normal(0, idio_sd, n)
            market_level = np.cumsum(market_ret)

            for t, d in enumerate(dates):
                # Reporting gaps are intentional to exercise coverage/missingness logic.
                if rng.random() < (0.035 if m.state != "Kerala" else 0.09):
                    continue
                doy = d.dayofyear
                seasonal = 1 + 0.10 * math.sin(2 * math.pi * (doy + 18) / 365.25)
                rain, temp = weather_cache[(m.market, d)]
                weather_pressure = spec["weather_sens"] * max(0, rain - 35) / 100
                heat_pressure = (0.11 if commodity == "Tomato" else 0.03) * max(0, temp - 35) / 10

                arrival_season = 1 + 0.25 * math.sin(2 * math.pi * (doy + 130) / 365.25)
                arrivals = spec["arrival_base"] * arrival_season * (1 - min(0.55, rain / 180))
                arrivals *= rng.lognormal(mean=0, sigma=0.18)
                arrivals = max(8, arrivals)

                supply_pressure = 0.045 * (spec["arrival_base"] - arrivals) / spec["arrival_base"]
                trend = 1 + 0.00010 * t
                market_noise = rng.normal(0, 0.0015)
                price = spec["base"] * STATE_FACTOR[m.state] * seasonal * trend
                price *= math.exp(market_level[t] + supply_pressure + weather_pressure + heat_pressure + market_noise)
                price = float(np.clip(price, 250, 12000))
                spread = max(60, price * abs(rng.normal(0.075, 0.018)))
                min_p = max(1, price - spread)
                max_p = price + spread
                price_rows.append({
                    "date": d.date().isoformat(), "state": m.state, "district": m.district,
                    "market": m.market, "market_id": m.market_id, "commodity": commodity, "variety": "Demo Standard",
                    "grade": "FAQ", "min_price": round(min_p, 2), "max_price": round(max_p, 2),
                    "modal_price": round(price, 2), "arrivals": round(arrivals, 2),
                    "source": "AGRIFLOW_DEMO_SYNTHETIC", "data_mode": "DEMO"
                })

    prices = pd.DataFrame(price_rows)
    weather = pd.DataFrame(weather_rows)
    prices.to_csv(output_dir / "demo_market_daily.csv", index=False)
    weather.to_csv(output_dir / "demo_weather_daily.csv", index=False)
    market_df.to_csv(output_dir / "demo_markets.csv", index=False)
    return (
        output_dir / "demo_market_daily.csv",
        output_dir / "demo_weather_daily.csv",
        output_dir / "demo_markets.csv",
    )


if __name__ == "__main__":
    from agriflow.config import settings
    paths = generate_demo(settings.demo_dir)
    print("Generated demo data:")
    for p in paths:
        print(f" - {p}")
