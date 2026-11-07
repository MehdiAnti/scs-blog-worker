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


MAX_PHOTO_SIZE = 10 * 1024 * 1024


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

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=60.0,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/*,*/*",
        },
    ) as client:

        response = await client.get(photo)

    response.raise_for_status()

    image_data = response.content

    if not image_data:
        raise Exception("Downloaded image is empty")

    if len(image_data) > MAX_PHOTO_SIZE:
        raise Exception(
            "Image exceeds Telegram's 10 MB photo upload limit"
        )

    content_type = (
        response.headers.get(
            "content-type",
            "",
        )
        .split(";")[0]
        .strip()
        .lower()
    )

    if not content_type.startswith("image/"):
        raise Exception(
            f"Invalid image content type: {content_type}"
        )

    extensions = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }

    extension = extensions.get(
        content_type,
        "jpg",
    )

    token = get_bot_token(env)

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{token}/sendPhoto"
    )

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        response = await client.post(
            telegram_url,
            data={
                "chat_id": str(chat_id),
                "caption": caption,
                "parse_mode": "HTML",
            },
            files={
                "photo": (
                    f"hero.{extension}",
                    image_data,
                    content_type,
                ),
            },
        )

    if not response.is_success:
        raise Exception(response.text)

    data = response.json()

    if not data.get("ok"):
        raise Exception(response.text)

    return data


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
            photo["result"]["message_id"]
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

        reply_id = (
            photo_result["result"]["message_id"]
        )

    await send_rich_message(
        env,
        chat_id,
        rich_html,
        reply_id,
    )

    return article
