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

HTTP_TIMEOUT = httpx.Timeout(
    20.0,
    connect=8.0,
    read=20.0,
    write=20.0,
    pool=5.0,
)


async def _post(
    env,
    method,
    payload,
    timeout=HTTP_TIMEOUT,
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
        raise Exception(
            f"{method} HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    if not data.get("ok"):
        raise Exception(
            f"{method} failed: {response.text[:1000]}"
        )

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
    )


async def download_image(photo_url):
    print("Hero image download started")

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=HTTP_TIMEOUT,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/*,*/*",
        },
    ) as client:
        response = await client.get(photo_url)

    response.raise_for_status()

    image_data = response.content

    if not image_data:
        raise Exception("Downloaded image is empty")

    if len(image_data) > MAX_PHOTO_SIZE:
        raise Exception(
            "Image exceeds Telegram's 10 MB photo upload limit"
        )

    content_type = (
        response.headers.get("content-type", "")
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

    print(
        f"Hero image downloaded | "
        f"Size={len(image_data)} | "
        f"Type={content_type}"
    )

    return (
        image_data,
        content_type,
        extension,
    )


async def send_photo(
    env,
    chat_id,
    image_data,
    content_type,
    extension,
    caption,
):
    token = get_bot_token(env)

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{token}/sendPhoto"
    )

    print(
        f"Sending photo | Chat={chat_id} | "
        f"Size={len(image_data)}"
    )

    async with httpx.AsyncClient(
        timeout=HTTP_TIMEOUT
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
        raise Exception(
            f"sendPhoto HTTP {response.status_code}: "
            f"{response.text[:1000]}"
        )

    data = response.json()

    if not data.get("ok"):
        raise Exception(
            f"sendPhoto failed: {response.text[:1000]}"
        )

    print(
        f"Photo sent | Chat={chat_id}"
    )

    return data


async def send_rich_message(
    env,
    chat_id,
    html,
    reply_to_message_id=None,
):
    print(
        f"Sending rich message | Chat={chat_id} | "
        f"HTML length={len(html)}"
    )

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

    result = await _post(
        env,
        "sendRichMessage",
        payload,
    )

    print(
        f"Rich message sent | Chat={chat_id}"
    )

    return result


async def send_channel_article(
    env,
    preview,
    html,
    image_data=None,
    content_type=None,
    extension=None,
):
    if not get_post_to_channel(env):
        print("Channel publishing disabled")
        return None

    channel_id = get_channel_id(env)

    reply_id = None

    if image_data:
        photo = await send_photo(
            env,
            channel_id,
            image_data,
            content_type,
            extension,
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
    print(
        f"Article processing started | URL={article_url}"
    )

    article = await fetch_article(
        article_url
    )

    print(
        f"Article fetched | Title={article['title']}"
    )

    article_html = clean_article(
        article["html"]
    )

    print(
        f"Article cleaned | Length={len(article_html)}"
    )

    rich_html = build_rich_article(
        article_html
    )

    preview = build_preview(
        article["title"],
        article["url"],
        article["teaser"],
    )

    image_data = None
    content_type = None
    extension = None

    if article["hero_image"]:
        (
            image_data,
            content_type,
            extension,
        ) = await download_image(
            article["hero_image"]
        )

        admin_photo = await send_photo(
            env,
            chat_id,
            image_data,
            content_type,
            extension,
            preview[:1024],
        )

        admin_reply_id = (
            admin_photo["result"]["message_id"]
        )
    else:
        admin_reply_id = None

    if publish_channel:
        await send_channel_article(
            env,
            preview,
            rich_html,
            image_data,
            content_type,
            extension,
        )

    await send_rich_message(
        env,
        chat_id,
        rich_html,
        admin_reply_id,
    )

    print(
        f"Article processing completed | "
        f"URL={article['url']}"
    )

    return article
