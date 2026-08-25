import json

from config import (
    LATEST_ARTICLE_KEY,
    STATUS_KEY,
)


DEFAULT_ARTICLE = {
    "url": "",
    "title": "",
}


DEFAULT_STATUS = {
    "last_check": "",
    "last_result": "",
    "latest_title": "",
    "latest_url": "",
    "last_error": "",
}


def _normalize_url(url):
    return (
        (url or "")
        .replace("http://", "https://")
        .rstrip("/")
        .strip()
    )


async def get_last_article(env):
    value = await env.KV_BINDING.get(
        LATEST_ARTICLE_KEY
    )

    if not value:
        return DEFAULT_ARTICLE.copy()

    try:
        data = json.loads(value)

        return {
            "url": data.get("url", ""),
            "title": data.get("title", ""),
        }

    except Exception:
        return DEFAULT_ARTICLE.copy()


async def article_is_new(env, article_url):
    stored = await get_last_article(env)

    return (
        _normalize_url(article_url)
        !=
        _normalize_url(stored.get("url", ""))
    )


async def save_detected(env, url, title):
    payload = {
        "url": _normalize_url(url),
        "title": title,
    }

    await env.KV_BINDING.put(
        LATEST_ARTICLE_KEY,
        json.dumps(payload),
    )


async def get_status(env):
    value = await env.KV_BINDING.get(
        STATUS_KEY
    )

    if not value:
        return DEFAULT_STATUS.copy()

    try:
        data = json.loads(value)

        return {
            "last_check": data.get("last_check", ""),
            "last_result": data.get("last_result", ""),
            "latest_title": data.get("latest_title", ""),
            "latest_url": data.get("latest_url", ""),
            "last_error": data.get("last_error", ""),
        }

    except Exception:
        return DEFAULT_STATUS.copy()


async def save_status(env, status):
    await env.KV_BINDING.put(
        STATUS_KEY,
        json.dumps(status),
    )
