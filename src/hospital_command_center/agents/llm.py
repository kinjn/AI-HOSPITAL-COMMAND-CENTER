"""Shared LLM client factory."""

from langchain_openai import ChatOpenAI

from hospital_command_center.core.config import get_settings
from hospital_command_center.core.exceptions import NotConfiguredError


def get_chat_model(max_tokens: int = 4096) -> ChatOpenAI:
    settings = get_settings()
    '''if not settings.llm_api_key.strip():
        raise NotConfiguredError(
            "OPENAI_API_KEY is not set. Add it to your .env file to enable LLM triage."
        )'''
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        temperature=settings.llm_temperature,
        max_tokens=max_tokens,
    )