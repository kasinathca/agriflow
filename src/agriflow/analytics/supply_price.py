from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from scipy import stats


def supply_price_stats(df: pd.DataFrame, min_n: int = 20) -> dict[str, float | int | None]:
    """Descriptive arrival–price association with sample and variation guards.

    Constant arrival or price series are valid empirical inputs but do not define a
    correlation/regression slope.  Such cases return ``None`` statistics instead of
    raising, allowing the broader analysis pipeline to retain and report the market.
    """
    x = df[["arrivals", "modal_price"]].dropna().copy()
    x = x[(x.arrivals >= 0) & (x.modal_price > 0)]
    n = len(x)
    empty = {
        "n": n,
        "spearman_rho": None,
        "spearman_p": None,
        "loglog_beta": None,
        "beta_p": None,
        "r_squared": None,
    }
    if n < min_n:
        return empty

    arrivals_vary = x["arrivals"].nunique(dropna=True) >= 2
    prices_vary = x["modal_price"].nunique(dropna=True) >= 2
    if arrivals_vary and prices_vary:
        rho, p = spearmanr(x.arrivals, x.modal_price)
        empty["spearman_rho"] = float(rho) if np.isfinite(rho) else None
        empty["spearman_p"] = float(p) if np.isfinite(p) else None

    lx = np.log1p(x.arrivals.to_numpy(dtype=float))
    ly = np.log(x.modal_price.to_numpy(dtype=float))
    if np.ptp(lx) > 0 and np.ptp(ly) > 0:
        slope, _intercept, r, p_beta, _ = stats.linregress(lx, ly)
        empty["loglog_beta"] = float(slope)
        empty["beta_p"] = float(p_beta)
        empty["r_squared"] = float(r * r)
    return empty
