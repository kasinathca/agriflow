from __future__ import annotations

"""Data-source provenance vocabulary and source-tier inference.

Source tiers deliberately separate empirical authenticity from source authority:
REAL means an observation came from a non-synthetic source, while source_tier records
how directly that observation can be traced to the official/curated provider.
"""

from collections.abc import Iterable

PRIMARY_OFFICIAL = "PRIMARY_OFFICIAL"
CURATED_OFFICIAL_DERIVED = "CURATED_OFFICIAL_DERIVED"
SECONDARY_MIRROR = "SECONDARY_MIRROR"
USER_SUPPLIED = "USER_SUPPLIED"
DEMO = "DEMO"
UNKNOWN = "UNKNOWN"

PAPER_ACCEPTABLE_TIERS = {PRIMARY_OFFICIAL, CURATED_OFFICIAL_DERIVED}
ALL_TIERS = {
    PRIMARY_OFFICIAL,
    CURATED_OFFICIAL_DERIVED,
    SECONDARY_MIRROR,
    USER_SUPPLIED,
    DEMO,
    UNKNOWN,
}


def infer_source_tier(source: str, data_mode: str = "") -> str:
    """Infer a conservative source tier from a canonical source label."""
    mode = str(data_mode).strip().upper()
    src = str(source).strip().upper()
    if mode == "DEMO" or src.startswith("DEMO"):
        return DEMO
    if "DATA_GOV" in src or "AGMARKNET_OFFICIAL" in src:
        return PRIMARY_OFFICIAL
    if "CEDA" in src:
        return CURATED_OFFICIAL_DERIVED
    if "MIRROR" in src or "ARCHIVE" in src:
        return SECONDARY_MIRROR
    if src in {"", "USER_IMPORT", "USER_SUPPLIED"}:
        return USER_SUPPLIED if mode != "DEMO" else DEMO
    return USER_SUPPLIED


def split_tiers(values: Iterable[str]) -> set[str]:
    """Split aggregate comma-separated tier labels into a normalized set."""
    out: set[str] = set()
    for value in values:
        for part in str(value).split(","):
            tier = part.strip().upper()
            if tier:
                out.add(tier)
    return out


def tiers_are_paper_acceptable(tiers: Iterable[str]) -> bool:
    observed = split_tiers(tiers)
    return bool(observed) and observed <= PAPER_ACCEPTABLE_TIERS
