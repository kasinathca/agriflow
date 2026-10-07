from __future__ import annotations

import time
from typing import Any
import requests


class SourceError(RuntimeError):
    pass


class HttpClient:
    def __init__(self, timeout: int = 30, retries: int = 3):
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "AgriFlow-Academic-Project/1.2"})

    def request_json(self, method: str, url: str, **kwargs: Any) -> Any:
        last: Exception | None = None
        for attempt in range(self.retries):
            try:
                r = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if r.status_code == 429:
                    time.sleep(2 ** (attempt + 1))
                    continue
                r.raise_for_status()
                return r.json()
            except (requests.RequestException, ValueError) as exc:
                last = exc
                if attempt < self.retries - 1:
                    time.sleep(1.5 * (attempt + 1))
        raise SourceError(f"Request failed after {self.retries} attempts: {url}: {last}")
