from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def estimate_token_proxy(messages: list[dict[str, str]], content: str = "") -> int:
    chars = sum(len(item.get("content", "")) for item in messages) + len(content)
    return max(1, chars // 4)


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_json_content(content: str) -> Any:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_escape_control_chars_inside_strings(text))


def _escape_control_chars_inside_strings(text: str) -> str:
    escaped: list[str] = []
    in_string = False
    escape = False
    for char in text:
        if escape:
            escaped.append(char)
            escape = False
            continue
        if char == "\\":
            escaped.append(char)
            escape = True
            continue
        if char == '"':
            escaped.append(char)
            in_string = not in_string
            continue
        if in_string and char in {"\n", "\r", "\t"}:
            escaped.append({"\n": "\\n", "\r": "\\r", "\t": "\\t"}[char])
        else:
            escaped.append(char)
    return "".join(escaped)


def call_chat_completion(messages: list[dict[str, str]], llm_config: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    model = llm_config.get("model", "deepseek-chat")
    api_key_env = llm_config.get("api_key_env", "LLM_API_KEY")
    base_url_env = llm_config.get("base_url_env", "LLM_BASE_URL")
    api_key = os.environ.get(api_key_env)
    base_url = os.environ.get(base_url_env)
    timeout = float(llm_config.get("timeout_sec", 30))
    temperature = float(llm_config.get("temperature", 0.3))
    max_tokens = int(llm_config.get("max_tokens", 800))
    max_retries = int(llm_config.get("max_retries", 3))

    if not api_key:
        return _failure(model, "Missing LLM_API_KEY.", start, messages)
    if not base_url:
        return _failure(model, "Missing LLM_BASE_URL.", start, messages)

    try:
        import requests
    except Exception as exc:
        return _failure(model, f"requests import failed: {exc}", start, messages)

    clean_base_url = base_url.rstrip("/")
    url = clean_base_url + "/chat/completions" if clean_base_url.endswith("/v1") else clean_base_url + "/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    last_error = ""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Connection": "close"},
                json=payload,
                timeout=timeout,
            )
            if response.status_code >= 400:
                return _failure(model, f"HTTP {response.status_code}: {response.text}", start, messages)
            try:
                body = response.json()
            except Exception as exc:
                return _failure(model, f"Response is not JSON: {exc}", start, messages)
            choices = body.get("choices") or []
            if not choices:
                return _failure(model, f"Response missing choices: {body}", start, messages)
            content = choices[0].get("message", {}).get("content", "")
            try:
                parsed = parse_json_content(content)
            except Exception as exc:
                return _failure(model, f"LLM JSON parse failed: {exc}; content={content}", start, messages, content)
            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            return {
                "success": True,
                "backend": "llm_api",
                "model": model,
                "content": content,
                "json": parsed,
                "error": None,
                "duration_ms": duration_ms,
                "token_proxy": estimate_token_proxy(messages, content),
                "attempts": attempt,
            }
        except requests.Timeout as exc:
            last_error = f"LLM request timeout: {exc}"
        except Exception as exc:
            last_error = f"LLM request failed: {exc}"
        if attempt < max_retries:
            time.sleep(min(2.0, 0.5 * attempt))
    return _failure(model, f"{last_error}; attempts={max_retries}", start, messages)


def _failure(model: str, error: str, start: float, messages: list[dict[str, str]], content: str = "") -> dict[str, Any]:
    return {
        "success": False,
        "backend": "llm_api",
        "model": model,
        "content": content,
        "json": None,
        "error": error,
        "duration_ms": round((time.perf_counter() - start) * 1000, 3),
        "token_proxy": estimate_token_proxy(messages, content),
    }

