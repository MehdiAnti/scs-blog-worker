import hashlib
import json

from config import (
    LATEST_ARTICLE_KEY,
    STATUS_KEY,
    PUBLISH_SETTINGS_KEY,
    get_post_to_channel,
    get_send_to_admin,
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


PUBLISH_STATE_PREFIX = "publish_state:"


def _normalize_url(url):
    return (
        (url or "")
        .replace("http://", "https://")
        .rstrip("/")
        .strip()
    )


def get_publish_state_key(article_url):
    normalized_url = _normalize_url(article_url)

    digest = hashlib.sha256(
        normalized_url.encode("utf-8")
    ).hexdigest()

    return f"{PUBLISH_STATE_PREFIX}{digest}"


async def get_publish_state(env, key):
    value = await env.KV_BINDING.get(key)

    if not value:
        return {}

    try:
        data = json.loads(value)

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


async def save_publish_state(env, key, state):
    await env.KV_BINDING.put(
        key,
        json.dumps(state),
    )


async def clear_publish_state(env, article_url):
    key = get_publish_state_key(article_url)

    await env.KV_BINDING.delete(key)


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


async def get_publish_settings(env):
    settings = {
        "post_to_channel": get_post_to_channel(env),
        "send_to_admin": get_send_to_admin(env),
    }

    value = await env.KV_BINDING.get(
        PUBLISH_SETTINGS_KEY
    )

    if not value:
        return settings

    try:
        stored = json.loads(value)

        if not isinstance(stored, dict):
            return settings

        for key in (
            "post_to_channel",
            "send_to_admin",
        ):
            if type(stored.get(key)) is bool:
                settings[key] = stored[key]

    except Exception as e:
        print(
            "Publishing settings read failed:",
            repr(e),
        )

    return settings


async def save_publish_settings(env, settings):
    current = await get_publish_settings(env)

    for key in (
        "post_to_channel",
        "send_to_admin",
    ):
        if (
            key in settings
            and type(settings[key]) is bool
        ):
            current[key] = settings[key]

    await env.KV_BINDING.put(
        PUBLISH_SETTINGS_KEY,
        json.dumps(current),
    )

    return current
