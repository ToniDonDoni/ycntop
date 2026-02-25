from __future__ import annotations

import logging
import os
import shlex
import ssl
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 10
MAX_RETRIES = 2
BACKOFF_FACTOR = 1.5
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) "
    "Gecko/20100101 Firefox/135.0"
)


def _build_ssl_context() -> ssl.SSLContext:
    if os.getenv("YYC_INSECURE_SSL", "").lower() in {"1", "true", "yes"}:
        LOGGER.warning("YYC_INSECURE_SSL is enabled; TLS certificate verification is disabled.")
        return ssl._create_unverified_context()
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _build_repro_curl(url: str, *, timeout: int) -> str:
    insecure = os.getenv("YYC_INSECURE_SSL", "").lower() in {"1", "true", "yes"}
    parts = [
        "curl",
        "-L",
        "--compressed",
        "-A",
        USER_AGENT,
        "-H",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H",
        "Accept-Language: en-US,en;q=0.5",
        "--max-time",
        str(timeout),
    ]
    if insecure:
        parts.append("-k")
    parts.append(url)
    return " ".join(shlex.quote(p) for p in parts)


def fetch_url(url: str, *, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch raw HTML/text for the target URL with retries."""

    ssl_context = _build_ssl_context()
    last_err: Optional[Exception] = None
    repro_logged = False
    for attempt in range(MAX_RETRIES + 1):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=timeout, context=ssl_context) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="ignore")
        except (HTTPError, URLError, TimeoutError) as err:
            last_err = err
            wait = BACKOFF_FACTOR ** attempt
            LOGGER.warning("fetch_url failed for %s (attempt %s/%s): %s", url, attempt + 1, MAX_RETRIES + 1, err)
            if not repro_logged:
                LOGGER.warning("Repro command: %s", _build_repro_curl(url, timeout=timeout))
                repro_logged = True
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")
