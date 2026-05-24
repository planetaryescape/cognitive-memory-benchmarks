"""OpenAI client helpers for benchmark harnesses.

`OPENAI_CHAT_BASE_URL` lets local OpenAI-compatible chat servers handle
extraction, answer generation, reranking, and judging while embeddings keep
using the normal OpenAI endpoint.
"""

from __future__ import annotations

import os
from typing import Any


def make_chat_client(**kwargs: Any):
    from openai import OpenAI

    chat_base_url = os.getenv("OPENAI_CHAT_BASE_URL")
    chat_api_key = os.getenv("OPENAI_CHAT_API_KEY")
    chat_timeout = os.getenv("OPENAI_CHAT_TIMEOUT")
    if chat_timeout and "timeout" not in kwargs:
        kwargs["timeout"] = float(chat_timeout)
    if chat_base_url:
        kwargs["base_url"] = chat_base_url
        kwargs["api_key"] = chat_api_key or "local-chat"
    elif chat_api_key:
        kwargs["api_key"] = chat_api_key
    return OpenAI(**kwargs)
