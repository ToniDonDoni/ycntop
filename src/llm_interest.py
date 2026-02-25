from __future__ import annotations

import json
import logging
import os
import re
import ssl
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError
from urllib.request import Request, urlopen

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4.1-mini"
LLM_TIMEOUT_SECONDS = 25
# Empirical cap: ~24h HN runs were around this range, so 110 avoids early cutoffs.
DEFAULT_MAX_CALLS = 110
LOGGER = logging.getLogger(__name__)
_budget_max_calls = DEFAULT_MAX_CALLS
_budget_calls_used = 0
_budget_limit_reached = False
_llm_insecure_ssl = False
_llm_ssl_context: Optional[ssl.SSLContext] = None


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
    global _budget_max_calls, _budget_calls_used, _budget_limit_reached
    _budget_max_calls = max(0, int(max_calls))
    _budget_calls_used = 0
    _budget_limit_reached = False


def get_llm_budget_state() -> Dict[str, int]:
    return {
        "max_calls": _budget_max_calls,
        "calls_used": _budget_calls_used,
        "limit_reached": 1 if _budget_limit_reached else 0,
    }


def score_title_with_llm(title: str) -> LLMInterestResult:
    global _budget_calls_used, _budget_limit_reached
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    if not api_key:
        return LLMInterestResult(score=0.0, reason="OPENAI_API_KEY not set", status="no_api_key", model=model)
    if _budget_calls_used >= _budget_max_calls:
        _budget_limit_reached = True
        return LLMInterestResult(
            score=0.0,
            reason=f"LLM call limit reached ({_budget_max_calls})",
            status="limit_reached",
            model=model,
        )
    _budget_calls_used += 1

    prompt = (
        "Rate how interesting this technology/news title is for a technical engineering audience.\n"
        "Title: "
        f"{title}\n"
        "Return strict JSON only with keys: score, reason.\n"
        "Constraints: score must be a number from 0 to 8, reason <= 18 words."
    )
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

    LOGGER.info(
        "Calling OpenAI LLM scoring API (model=%s, timeout=%ss, call=%s/%s) for title %r",
        model,
        LLM_TIMEOUT_SECONDS,
        _budget_calls_used,
        _budget_max_calls,
        title,
    )

    try:
        with urlopen(req, timeout=LLM_TIMEOUT_SECONDS, context=_get_llm_ssl_context()) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            err_body = ""
        err_preview = (err_body[:240] + "...") if len(err_body) > 240 else err_body
        LOGGER.warning(
            "LLM scoring HTTP error for title %r: status=%s body=%r",
            title,
            exc.code,
            err_preview,
        )
        return LLMInterestResult(
            score=0.0,
            reason=f"LLM HTTP error {exc.code}",
            status="error",
            model=model,
        )
    except Exception as exc:
        LOGGER.warning("LLM scoring failed for title %r: %s", title, exc)
        return LLMInterestResult(score=0.0, reason=f"LLM unavailable: {exc}", status="error", model=model)

    text = body.get("output_text") if isinstance(body, dict) else None
    if not text:
        text = _extract_text_from_output(body)

    parsed = _parse_json_fragment(text or "")
    if not parsed:
        LOGGER.warning("LLM scoring parse error for title %r: raw output was not valid JSON", title)
        return LLMInterestResult(score=0.0, reason="LLM returned invalid JSON", status="parse_error", model=model)

    score = _clamp_score(parsed.get("score", 0))
    reason = str(parsed.get("reason", "")).strip() or "LLM score without explanation"
    return LLMInterestResult(score=score, reason=reason, status="ok", model=model)


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
