from __future__ import annotations

import unicodedata

STATE_ALIASES = {
    "nct of delhi": "Delhi",
    "delhi (nct)": "Delhi",
    "orissa": "Odisha",
    "odisha": "Odisha",
    "andaman & nicobar island": "Andaman and Nicobar Islands",
    "andaman & nicobar islands": "Andaman and Nicobar Islands",
    "andaman and nicobar island": "Andaman and Nicobar Islands",
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "dadra & nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "daman & diu": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "pondicherry": "Puducherry",
    "jammu & kashmir": "Jammu and Kashmir",
    "jammu and kashmir": "Jammu and Kashmir",
    "uttaranchal": "Uttarakhand",
}


def canonical_state(value: object) -> str:
    s = str(value or "").strip()
    if not s:
        return s
    # Boundary providers sometimes transliterate Indian state names with macrons
    # (for example ``Mahārāshtra``).  Strip combining marks before applying the
    # provider-independent aliases so both boundary and mandi names converge.
    ascii_name = "".join(
        char
        for char in unicodedata.normalize("NFKD", s)
        if not unicodedata.combining(char)
    )
    key = " ".join(ascii_name.lower().split())
    return STATE_ALIASES.get(key, ascii_name.title())
