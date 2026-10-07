from __future__ import annotations

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
    key = " ".join(s.lower().split())
    return STATE_ALIASES.get(key, s)
