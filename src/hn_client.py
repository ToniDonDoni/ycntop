from __future__ import annotations

import json
import logging
import os
import ssl
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .models import HNStory

LOGGER = logging.getLogger(__name__)
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
DEFAULT_TIMEOUT = 10
MAX_WORKERS = 8
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:135.0) "
    "Gecko/20100101 Firefox/135.0"
)


def _build_ssl_context() -> ssl.SSLContext:
    """Return SSL context for HN API requests.

    Default behavior verifies TLS certificates. If the local trust store is
    broken, users can set YYC_INSECURE_SSL=1 to bypass verification.
    """

    if os.getenv("YYC_INSECURE_SSL", "").lower() in {"1", "true", "yes"}:
        LOGGER.warning("YYC_INSECURE_SSL is enabled; TLS certificate verification is disabled.")
        return ssl._create_unverified_context()

    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def unix_to_datetime(timestamp: int) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def is_within_hours(timestamp: int, hours: int, *, now: Optional[datetime] = None) -> bool:
    current = now or _utc_now()
    cutoff = current - timedelta(hours=hours)
    story_time = unix_to_datetime(timestamp)
    return story_time >= cutoff


def filter_recent_items(items: Iterable[Dict[str, int]], *, hours: int, now: Optional[datetime] = None) -> List[Dict[str, int]]:
    """Filter raw HN API items by recency.

    Items are expected to have a "time" field with a unix timestamp.
    """

    current = now or _utc_now()
    cutoff = current - timedelta(hours=hours)
    recent: List[Dict[str, int]] = []
    for item in items:
        ts = item.get("time")
        if ts is None:
            continue
        if unix_to_datetime(ts) >= cutoff:
            recent.append(item)
    return recent


class HNClient:
    def __init__(self, *, base_url: str = HN_API_BASE, timeout: int = DEFAULT_TIMEOUT, max_workers: int = MAX_WORKERS) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_workers = max_workers
        self.ssl_context = _build_ssl_context()

    # Public API -----------------------------------------------------------------
    def fetch_recent_stories(
        self,
        *,
        hours: int,
        max_items: int,
        endpoints: Optional[List[str]] = None,
    ) -> List[HNStory]:
        endpoints = endpoints or ["topstories", "newstories"]
        story_ids = self._load_story_id_pool(endpoints)
        if not story_ids:
            return []

        stories: List[HNStory] = []
        cutoff = _utc_now() - timedelta(hours=hours)
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_map = {executor.submit(self._fetch_story, story_id): story_id for story_id in story_ids[: max_items * 4]}
            for future in as_completed(future_map):
                story = future.result()
                if not story:
                    continue
                if story.time < cutoff:
                    continue
                stories.append(story)
                if len(stories) >= max_items * 2:
                    # Enough buffer for downstream filtering
                    break
        return stories

    # Internal helpers -----------------------------------------------------------
    def _load_story_id_pool(self, endpoints: List[str]) -> List[int]:
        seen = set()
        combined: List[int] = []
        for endpoint in endpoints:
            try:
                ids = self._get_json(f"{self.base_url}/{endpoint}.json") or []
            except Exception as exc:  # pragma: no cover - defensive branch
                LOGGER.warning("Failed to load ids from %s: %s", endpoint, exc)
                continue
            for story_id in ids:
                if story_id in seen:
                    continue
                seen.add(story_id)
                combined.append(story_id)
        return combined

    def _fetch_story(self, story_id: int) -> Optional[HNStory]:
        try:
            payload = self._get_json(f"{self.base_url}/item/{story_id}.json")
        except Exception as exc:  # pragma: no cover - network defensive path
            LOGGER.debug("Failed to fetch story %s: %s", story_id, exc)
            return None
        if not payload or payload.get("type") != "story" or "url" not in payload:
            return None
        story_time = payload.get("time")
        if not isinstance(story_time, int):
            return None
        return HNStory(
            id=payload["id"],
            title=payload.get("title", "(untitled)"),
            url=payload["url"],
            by=payload.get("by", "unknown"),
            score=int(payload.get("score", 0) or 0),
            descendants=int(payload.get("descendants", 0) or 0),
            time=unix_to_datetime(story_time),
            type=payload.get("type", "story"),
            text=payload.get("text"),
        )

    def _get_json(self, url: str):
        request = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                data = response.read().decode(charset)
                return json.loads(data)
        except URLError as err:  # pragma: no cover - network defensive path
            LOGGER.error("Network error while calling %s: %s", url, err)
            raise
