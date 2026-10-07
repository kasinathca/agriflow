from __future__ import annotations
import numpy as np
import pandas as pd

from agriflow.data.identity import ensure_market_id


def price_dispersion(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    x=ensure_market_id(df)
    rows=[]
    for (date, commodity), g in x.groupby(["date","commodity"], sort=True):
        g=g.drop_duplicates("market_id") if "market_id" in g.columns else g
        s=g["modal_price"].dropna().astype(float)
        if len(s)<2:
            rows.append({"date":date,"commodity":commodity,"markets":len(s),"median_price":s.median() if len(s) else np.nan,"iqr":np.nan,"mad":np.nan,"cv":np.nan,"relative_gap":np.nan})
            continue
        med=s.median();q10,q25,q75,q90=s.quantile([.10,.25,.75,.90]);mean=s.mean()
        rows.append({"date":date,"commodity":commodity,"markets":len(s),"median_price":med,"iqr":q75-q25,"mad":(s-med).abs().median(),"cv":s.std(ddof=1)/mean if mean else np.nan,"relative_gap":(q90-q10)/med if med else np.nan})
    return pd.DataFrame(rows)
