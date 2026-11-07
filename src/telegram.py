import httpx

from config import (
    get_bot_token,
    get_channel_id,
    get_post_to_channel,
)

from blogger import fetch_article

from html_build import (
    clean_article,
    build_preview,
    build_rich_article,
)


async def diagnose_image_url(label, url):

    print(f"[IMAGE DIAG] START: {label}")
    print(f"[IMAGE DIAG] REQUEST URL: {url}")

    try:

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=45.0,
        ) as client:

            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "image/*,*/*",
                },
            )

        print(
            f"[IMAGE DIAG] {label} STATUS:",
            response.status_code,
        )

        print(
            f"[IMAGE DIAG] {label} FINAL URL:",
            str(response.url),
        )

        print(
            f"[IMAGE DIAG] {label} CONTENT TYPE:",
            response.headers.get("content-type"),
        )

        print(
            f"[IMAGE DIAG] {label} CONTENT LENGTH HEADER:",
            response.headers.get("content-length"),
        )

        print(
            f"[IMAGE DIAG] {label} ACTUAL SIZE:",
            len(response.content),
        )

        print(
            f"[IMAGE DIAG] {label} REDIRECTS:",
            [
                str(item.url)
                for item in response.history
            ],
        )

        print(
            f"[IMAGE DIAG] {label} FIRST 16 BYTES:",
            response.content[:16].hex(),
        )

    except Exception as e:

        print(
            f"[IMAGE DIAG] {label} ERROR:",
            type(e).__name__,
            str(e),
        )


async def _post(
    env,
    method,
    payload,
    timeout=120.0,
):

    token = get_bot_token(env)

    url = (
        f"https://api.telegram.org/"
        f"bot{token}/{method}"
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        response = await client.post(
            url,
            json=payload,
        )

    if not response.is_success:
        raise Exception(response.text)

    data = response.json()

    if not data.get("ok"):
        raise Exception(response.text)

    return data


async def send_message(
    env,
    chat_id,
    text,
):

    return await _post(
        env,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=60.0,
    )


async def send_photo(
    env,
    chat_id,
    photo,
    caption,
):

    return await _post(
        env,
        "sendPhoto",
        {
            "chat_id": chat_id,
            "photo": photo,
            "caption": caption,
            "parse_mode": "HTML",
        },
        timeout=60.0,
    )


async def send_rich_message(
    env,
    chat_id,
    html,
    reply_to_message_id=None,
):

    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "html": html,
        },
    }

    if reply_to_message_id:

        payload["reply_parameters"] = {
            "message_id": reply_to_message_id,
        }

    return await _post(
        env,
        "sendRichMessage",
        payload,
        timeout=120.0,
    )


async def send_channel_article(
    env,
    preview,
    html,
    hero_image=None,
):

    if not get_post_to_channel(env):
        return None

    channel_id = get_channel_id(env)

    reply_id = None

    if hero_image:

        photo = await send_photo(
            env,
            channel_id,
            hero_image,
            preview[:1024],
        )

        reply_id = (
            photo["result"]
            ["message_id"]
        )

    return await send_rich_message(
        env,
        channel_id,
        html,
        reply_id,
    )


async def send_article(
    env,
    chat_id,
    article_url,
    publish_channel=False,
):

    article = await fetch_article(
        article_url
    )

    print(
        "[IMAGE DIAG] SELECTED HERO:",
        article["hero_image"],
    )

    await diagnose_image_url(
        "WUJЕK_BOНUN",
        "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEg2nIzq-57rWcF817SZtaNprAXfd5-I7OBJykv8ikfYFNTaPra9X5IzjIeWCg-pTwjanTnMnohKxoGcl0jxzOHhOY8WqUssIfqQJdd5xf96B3U6iWe0__mOCLZJlqRW21XGO3bQvl8eYki3O6EDFxBQM_hbZN_a3WQ6gjTcBC7y8cIbM7GriYmukiC-kPs/s1920/SOTR_ThumbnailFHD.jpg",
    )

    await diagnose_image_url(
        "PINKTOBER",
        "https://blogger.googleusercontent.com/img/b/R29vZ2xl/AVvXsEjsrk513MY-aISsWKpXHe8cZtLS98Xr1NLgCt82ULcQoMiMbpvk_h5ntTGATJU17ugMPv6PYJVWgofzbsPVV1bf43ihgVIwIdt3mMT4kO5T00MHdSpn6vBnIGpcyin_Qg_5JwvREUNG8bojf6tLMsTqW3oO8rEIQDhs_q3QPwOvAyUMjgY0IzDisR0Q/s1920/Socmedia_1920x1080_Pinktober_2026_Conclusion.jpg",
    )

    article_html = clean_article(
        article["html"]
    )

    rich_html = build_rich_article(
        article_html
    )

    preview = build_preview(
        article["title"],
        article["url"],
        article["teaser"],
    )

    photo_result = None

    if article["hero_image"]:

        photo_result = await send_photo(
            env,
            chat_id,
            article["hero_image"],
            preview[:1024],
        )

    if publish_channel:

        await send_channel_article(
            env,
            preview,
            rich_html,
            article["hero_image"],
        )

    reply_id = None

    if photo_result:

        try:

            reply_id = (
                photo_result["result"]
                ["message_id"]
            )

        except Exception:
            pass

    await send_rich_message(
        env,
        chat_id,
        rich_html,
        reply_id,
    )

    return article
