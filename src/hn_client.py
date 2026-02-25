from __future__ import annotations

import json
import logging
import os
import ssl
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from .models import HNStory

LOGGER = logging.getLogger(__name__)
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
DEFAULT_TIMEOUT = 10
MAX_WORKERS = 8
# Do not stop on the first old item: newstories ordering is not strictly monotonic
# by timestamp, so one old record can appear before still-valid fresh records.
OLD_STREAK_EARLY_STOP = 25
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
        max_items: Optional[int] = None,
        endpoints: Optional[List[str]] = None,
    ) -> List[HNStory]:
        endpoints = endpoints or ["newstories"]
        story_ids = self._load_story_id_pool(endpoints)
        if not story_ids:
            return []

        stories: List[HNStory] = []
        scan_now = _utc_now()
        cutoff = scan_now - timedelta(hours=hours)
        ids_to_fetch = story_ids if max_items is None else story_ids[: max_items * 4]
        old_streak = 0
        processed = 0
        newest_seen_time: Optional[datetime] = None
        oldest_seen_time: Optional[datetime] = None
        for story_id in ids_to_fetch:
            story = self._fetch_story(story_id)
            if not story:
                continue
            processed += 1
            if newest_seen_time is None or story.time > newest_seen_time:
                newest_seen_time = story.time
            if oldest_seen_time is None or story.time < oldest_seen_time:
                oldest_seen_time = story.time
            oldest_age_h = (scan_now - oldest_seen_time).total_seconds() / 3600 if oldest_seen_time else 0.0
            hours_to_cutoff = max(0.0, hours - oldest_age_h)
            status = "fresh" if story.time >= cutoff else "old"
            LOGGER.info(
                "HN scan progress: processed=%s candidates=%s item_id=%s item_time=%s status=%s newest=%s oldest=%s (oldest_age_h=%.2f, to_cutoff_h=%.2f)",
                processed,
                len(stories),
                story.id,
                story.time.isoformat(),
                status,
                newest_seen_time.isoformat() if newest_seen_time else "n/a",
                oldest_seen_time.isoformat() if oldest_seen_time else "n/a",
                oldest_age_h,
                hours_to_cutoff,
            )
            if story.time < cutoff:
                old_streak += 1
                if max_items is None and old_streak >= OLD_STREAK_EARLY_STOP:
                    LOGGER.info(
                        "Stopping HN scan early after %s consecutive old stories (< cutoff %s)",
                        old_streak,
                        cutoff.isoformat(),
                    )
                    break
                continue
            old_streak = 0
            stories.append(story)
            if max_items is not None and len(stories) >= max_items * 2:
                # Enough buffer for downstream filtering
                break
        stories.sort(key=lambda s: (s.score, s.descendants, s.time), reverse=True)
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
        LOGGER.info("HN API request: url=%s timeout=%ss", url, self.timeout)
        started = time.perf_counter()
        try:
            with urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                data = response.read().decode(charset)
                elapsed_ms = (time.perf_counter() - started) * 1000
                LOGGER.info("HN API response: url=%s elapsed_ms=%.1f", url, elapsed_ms)
                return json.loads(data)
        except URLError as err:  # pragma: no cover - network defensive path
            elapsed_ms = (time.perf_counter() - started) * 1000
            LOGGER.error(
                "HN API error: url=%s timeout=%ss elapsed_ms=%.1f error=%s",
                url,
                self.timeout,
                elapsed_ms,
                err,
            )
            raise
