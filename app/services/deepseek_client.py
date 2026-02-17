import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

import requests

from ..config import settings


class DeepSeekRateLimiter:
    """
    DeepSeek API 简单限流器，基于时间窗口统计请求次数。
    """

    def __init__(self, max_per_minute: int) -> None:
        self._max_per_minute = max_per_minute
        self._timestamps: Deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """
        阻塞当前线程直到满足每分钟请求上限的约束。
        """

        while True:
            with self._lock:
                now = time.time()
                cutoff = now - 60.0
                while self._timestamps and self._timestamps[0] < cutoff:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._max_per_minute:
                    self._timestamps.append(now)
                    return

                wait_seconds = 60.0 - (now - self._timestamps[0])

            if wait_seconds > 0:
                time.sleep(min(wait_seconds, 1.0))


class DeepSeekClient:
    """
    DeepSeek API 客户端封装，负责请求发送、重试与结果解析。
    """

    def __init__(self) -> None:
        self._api_key = settings.deepseek_api_key
        self._base_url = settings.deepseek_base_url.rstrip("/")
        self._model = settings.deepseek_model
        self._timeout = settings.api_request_timeout
        self._max_retries = settings.api_max_retries
        self._rate_limiter = DeepSeekRateLimiter(settings.max_requests_per_minute)
        self._session = requests.Session()

    def generate_text(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.9,
        max_tokens: int = 2048,
        stop: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        调用 DeepSeek Chat Completions 接口生成文本。
        """

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            self._rate_limiter.acquire()
            start_ts = time.time()
            try:
                response = self._session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self._timeout,
                )
                latency_ms = (time.time() - start_ts) * 1000.0
                if response.status_code >= 500:
                    last_error = RuntimeError(
                        f"DeepSeek server error: {response.status_code}"
                    )
                else:
                    data = response.json()
                    content = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )
                    meta = {
                        "raw": data,
                        "latency_ms": latency_ms,
                        "request_id": data.get("id"),
                        "usage": data.get("usage"),
                    }
                    clean_text = self._clean_content(content)
                    return clean_text, meta
            except Exception as exc:
                last_error = exc

            backoff = min(2 ** attempt, 30)
            time.sleep(backoff)

        raise RuntimeError(f"DeepSeek API 调用失败: {last_error}")

    def _clean_content(self, content: str) -> str:
        """
        对模型输出的文本进行基础清洗，去除特殊符号与多余空白。
        """

        if not content:
            return ""

        cleaned = content.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = cleaned.replace("\u3000", " ").replace("\t", " ")
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")
        lines = [line.strip() for line in cleaned.split("\n")]
        return "\n".join(line for line in lines if line)


client = DeepSeekClient()

