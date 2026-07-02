from __future__ import annotations

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "paper-radar/0.2 (local research paper tracker)"


def build_session(retries: int = 3, backoff_factor: float = 0.5) -> Session:
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
