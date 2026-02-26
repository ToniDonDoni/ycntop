from __future__ import annotations

import json
import logging
import os
import re
import ssl
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-5.2"
LLM_TIMEOUT_SECONDS = 300
DEFAULT_BATCH_SIZE = 20
# Upper bound for LLM scoring calls per run; keeps near-complete coverage without clipping candidates.
DEFAULT_MAX_CALLS = 500
LOGGER = logging.getLogger(__name__)
_budget_max_calls = DEFAULT_MAX_CALLS
_budget_calls_used = 0
_budget_limit_reached = False
_llm_insecure_ssl = False
_llm_ssl_context: Optional[ssl.SSLContext] = None
_run_expected_calls: Optional[int] = None
_llm_enabled = True


@dataclass
class LLMInterestResult:
    score: float
    reason: str
    status: str
    model: str


def set_llm_insecure_ssl(enabled: bool) -> None:
    """Configure TLS verification mode for OpenAI requests in this process."""

    global _llm_insecure_ssl, _llm_ssl_context
    _llm_insecure_ssl = bool(enabled)
    _llm_ssl_context = None


def set_llm_enabled(enabled: bool) -> None:
    global _llm_enabled
    _llm_enabled = bool(enabled)


def _build_ssl_context(*, insecure: bool) -> ssl.SSLContext:
    if insecure:
        LOGGER.warning("Insecure TLS mode is enabled for OpenAI calls; certificate verification is disabled.")
        return ssl._create_unverified_context()
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _get_llm_ssl_context() -> ssl.SSLContext:
    global _llm_ssl_context
    if _llm_ssl_context is None:
        _llm_ssl_context = _build_ssl_context(insecure=_llm_insecure_ssl)
    return _llm_ssl_context


def reset_llm_budget(max_calls: int = DEFAULT_MAX_CALLS) -> None:
    global _budget_max_calls, _budget_calls_used, _budget_limit_reached, _run_expected_calls
    _budget_max_calls = max(0, int(max_calls))
    _budget_calls_used = 0
    _budget_limit_reached = False
    _run_expected_calls = None


def set_llm_expected_calls(expected_calls: int) -> None:
    global _run_expected_calls
    _run_expected_calls = max(0, min(int(expected_calls), _budget_max_calls))


def get_llm_budget_state() -> Dict[str, int]:
    return {
        "max_calls": _budget_max_calls,
        "calls_used": _budget_calls_used,
        "limit_reached": 1 if _budget_limit_reached else 0,
    }


def score_title_with_llm(title: str) -> LLMInterestResult:
    results = score_titles_with_llm_batch([title], batch_size=1)
    return results[0]


def score_titles_with_llm_batch(titles: List[str], *, batch_size: int = DEFAULT_BATCH_SIZE) -> List[LLMInterestResult]:
    global _budget_calls_used, _budget_limit_reached
    if not titles:
        return []

    if not _llm_enabled:
        return [
            LLMInterestResult(
                score=0.0,
                reason="LLM disabled by runtime flag",
                status="disabled",
                model=DEFAULT_MODEL,
            )
            for _ in titles
        ]

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if not api_key:
        return [LLMInterestResult(score=0.0, reason="OPENAI_API_KEY not set", status="no_api_key", model=model) for _ in titles]

    available = max(0, _budget_max_calls - _budget_calls_used)
    score_count = min(len(titles), available)
    if score_count < len(titles):
        _budget_limit_reached = True

    results: List[LLMInterestResult] = []
    normalized_batch_size = max(1, int(batch_size))
    expected_total = _run_expected_calls if _run_expected_calls is not None else _budget_max_calls

    for offset in range(0, score_count, normalized_batch_size):
        chunk = titles[offset : offset + normalized_batch_size]
        chunk_len = len(chunk)
        start_idx = _budget_calls_used + 1
        _budget_calls_used += chunk_len
        end_idx = _budget_calls_used
        LOGGER.info(
            "Calling OpenAI LLM scoring API (model=%s, timeout=%ss, calls=%s-%s/%s, batch_size=%s)",
            model,
            LLM_TIMEOUT_SECONDS,
            start_idx,
            end_idx,
            expected_total,
            chunk_len,
        )
        results.extend(_score_title_batch_with_llm(chunk, api_key=api_key, model=model))

    for _ in range(score_count, len(titles)):
        results.append(
            LLMInterestResult(
                score=0.0,
                reason=f"LLM call limit reached ({_budget_max_calls})",
                status="limit_reached",
                model=model,
            )
        )
    return results


def _score_title_batch_with_llm(titles: List[str], *, api_key: str, model: str) -> List[LLMInterestResult]:
    prompt_lines = [
        "Rate how interesting each technology/news title is for a technical engineering audience.",
        "Return strict JSON only as an array of objects with keys: index, score, reason.",
        "Constraints: score is a number from 0 to 8, reason <= 18 words.",
        "Titles:",
    ]
    for idx, title in enumerate(titles):
        prompt_lines.append(f"{idx}: {title}")
    prompt = "\n".join(prompt_lines)

    payload: Dict[str, Any] = {
        "model": model,
        "input": prompt,
        "temperature": 0,
    }
    req = Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=LLM_TIMEOUT_SECONDS, context=_get_llm_ssl_context()) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            body = json.loads(raw)
    except HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            err_body = ""
        err_preview = (err_body[:240] + "...") if len(err_body) > 240 else err_body
        LOGGER.warning("LLM scoring HTTP error for batch: status=%s body=%r", exc.code, err_preview)
        return [LLMInterestResult(score=0.0, reason=f"LLM HTTP error {exc.code}", status="error", model=model) for _ in titles]
    except Exception as exc:
        LOGGER.warning("LLM scoring failed for batch: %s", exc)
        return [LLMInterestResult(score=0.0, reason=f"LLM unavailable: {exc}", status="error", model=model) for _ in titles]

    text = body.get("output_text") if isinstance(body, dict) else None
    if not text:
        text = _extract_text_from_output(body)
    parsed = _parse_json_fragment_any(text or "")
    normalized = _normalize_batch_payload(parsed, expected_count=len(titles))
    if normalized is None:
        LOGGER.warning("LLM scoring parse error for batch: raw output was not valid JSON array payload")
        return [LLMInterestResult(score=0.0, reason="LLM returned invalid JSON", status="parse_error", model=model) for _ in titles]

    results: List[LLMInterestResult] = []
    for item in normalized:
        score = _clamp_score(item.get("score", 0))
        reason = str(item.get("reason", "")).strip() or "LLM score without explanation"
        status = str(item.get("status", "ok")).strip() or "ok"
        results.append(LLMInterestResult(score=score, reason=reason, status=status, model=model))
    LOGGER.info(
        "OpenAI LLM scoring batch response received (model=%s, timeout=%ss, batch_size=%s, avg_score=%.3f)",
        model,
        LLM_TIMEOUT_SECONDS,
        len(results),
        sum(r.score for r in results) / max(1, len(results)),
    )
    return results


def _extract_text_from_output(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    output = body.get("output")
    if not isinstance(output, list):
        return ""
    chunks = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") in {"output_text", "text"}:
                txt = part.get("text")
                if isinstance(txt, str):
                    chunks.append(txt)
    return "\n".join(chunks)


def _parse_json_fragment(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _parse_json_fragment_any(text: str) -> Optional[Any]:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"(\[.*\]|\{.*\})", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _normalize_batch_payload(payload: Any, *, expected_count: int) -> Optional[List[Dict[str, Any]]]:
    entries: Optional[List[Any]] = None
    if isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict):
        maybe_items = payload.get("items")
        if isinstance(maybe_items, list):
            entries = maybe_items
    if entries is None:
        return None

    by_index: Dict[int, Dict[str, Any]] = {}
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        try:
            idx = int(raw.get("index"))
        except Exception:
            continue
        if 0 <= idx < expected_count:
            by_index[idx] = raw
    normalized: List[Dict[str, Any]] = []
    for idx in range(expected_count):
        normalized.append(by_index.get(idx, {"score": 0, "reason": "LLM batch item missing", "status": "parse_error"}))
    return normalized


def _clamp_score(value: Any) -> float:
    try:
        num = float(value)
    except Exception:
        return 0.0
    if num < 0:
        return 0.0
    if num > 8:
        return 8.0
    return round(num, 3)
