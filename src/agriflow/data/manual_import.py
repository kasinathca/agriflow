from __future__ import annotations

"""Schema-tolerant import helpers for manually downloaded mandi CSV exports."""

import re
import pandas as pd


def _key(value: str) -> str:
    x = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower())
    return x.strip("_")


def _find_column(columns: list[str], predicates) -> str | None:
    keyed = [(c, _key(c)) for c in columns]
    for predicate in predicates:
        for original, normalized in keyed:
            if predicate(normalized):
                return original
    return None


def canonicalize_mandi_export(
    df: pd.DataFrame,
    *,
    state: str | None = None,
    district: str | None = None,
    market: str | None = None,
    commodity: str | None = None,
) -> pd.DataFrame:
    """Map common AGMARKNET/CEDA portal CSV headings into AgriFlow's raw schema.

    Metadata flags fill fields omitted by filtered portal downloads.  The function
    refuses to invent market/commodity identity when neither a column nor metadata
    value is present.
    """
    cols = list(df.columns)
    mapping: dict[str, str] = {}

    candidates = {
        "date": [lambda x: x in {"date", "reported_date", "arrival_date", "period"}, lambda x: "date" in x],
        "state": [lambda x: x in {"state", "state_name"}],
        "district": [lambda x: x in {"district", "district_name"}],
        "market": [lambda x: x in {"market", "market_name", "mandi", "mandi_name"}],
        "commodity": [lambda x: x in {"commodity", "commodity_name", "crop", "crop_name"}],
        "variety": [lambda x: x in {"variety", "variety_name"}],
        "grade": [lambda x: x in {"grade", "grade_name"}],
        "min_price": [lambda x: ("min" in x or "minimum" in x) and "price" in x],
        "max_price": [lambda x: ("max" in x or "maximum" in x) and "price" in x],
        "modal_price": [lambda x: ("modal" in x or "mode" in x) and "price" in x],
        "arrivals": [lambda x: any(t in x for t in ("arrival", "quantity", "qty")) and not ("date" in x)],
    }
    for target, predicates in candidates.items():
        source = _find_column(cols, predicates)
        if source is not None:
            mapping[source] = target

    out = df.rename(columns=mapping).copy()
    metadata = {"state": state, "district": district, "market": market, "commodity": commodity}
    for field, value in metadata.items():
        if field not in out.columns and value is not None:
            out[field] = value
        elif field in out.columns and value is not None:
            out[field] = out[field].fillna(value).replace("", value)

    required = ["date", "state", "market", "commodity", "modal_price"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(
            "Import cannot establish required field(s): " + ", ".join(missing)
            + ". Supply missing identity with --state/--district/--market/--commodity where appropriate."
        )
    if "district" not in out.columns:
        out["district"] = district or ""
    for col in ["variety", "grade", "min_price", "max_price", "arrivals"]:
        if col not in out.columns:
            out[col] = pd.NA if col in {"min_price", "max_price", "arrivals"} else ""
    return out
