import mimetypes
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


MAX_IMAGE_SIZE = 10 * 1024 * 1024


async def _post(
    env,
    method,
    payload,
    timeout=120.0,
    files=None,
):

    token = get_bot_token(env)

    url = (
        f"https://api.telegram.org/"
        f"bot{token}/{method}"
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        if files:

            response = await client.post(
                url,
                data=payload,
                files=files,
            )

        else:

            response = await client.post(
                url,
                json=payload,
            )

    try:
        data = response.json()
    except Exception:
        data = {
            "ok": False,
            "description": response.text,
        }

    if not response.is_success or not data.get("ok"):

        error = (
            f"Telegram API failure | "
            f"Method={method} | "
            f"Status={response.status_code} | "
            f"Response={response.text[:2000]}"
        )

        print(error)

        raise RuntimeError(error)

    return data


async def _download_image(url):

    if not url:
        return None

    print(
        f"Downloading hero image: {url}"
    )

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers={
            "User-Agent": "Mozilla/5.0",
        },
    ) as client:

        response = await client.get(url)

    response.raise_for_status()

    content_type = (
        response.headers.get(
            "content-type",
            "",
        )
        .split(";")[0]
        .lower()
    )

    if not content_type.startswith("image/"):

        raise RuntimeError(
            f"Invalid image content type: "
            f"{content_type or 'unknown'}"
        )

    if len(response.content) > MAX_IMAGE_SIZE:

        raise RuntimeError(
            "Hero image exceeds 10 MB"
        )

    if not response.content:

        raise RuntimeError(
            "Hero image is empty"
        )

    extension = mimetypes.guess_extension(
        content_type
    )

    if not extension:

        extension = ".jpg"

    filename = (
        f"scs-blog-hero{extension}"
    )

    print(
        f"Image downloaded | "
        f"Size={len(response.content)} | "
        f"Type={content_type}"
    )

    return {
        "content": response.content,
        "filename": filename,
        "content_type": content_type,
    }


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

    payload = {
        "chat_id": chat_id,
        "caption": caption,
        "parse_mode": "HTML",
    }

    if isinstance(photo, dict):

        files = {
            "photo": (
                photo["filename"],
                photo["content"],
                photo["content_type"],
            ),
        }

        return await _post(
            env,
            "sendPhoto",
            payload,
            timeout=60.0,
            files=files,
        )

    payload["photo"] = photo

    return await _post(
        env,
        "sendPhoto",
        payload,
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
            "message_id":
                reply_to_message_id,
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

        try:

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

            print(
                "Channel hero image uploaded"
            )

        except Exception as e:

            print(
                "Channel image failed:",
                str(e),
            )

    try:

        result = await send_rich_message(
            env,
            channel_id,
            html,
            reply_id,
        )

        print(
            "Channel rich message published"
        )

        return result

    except Exception as e:

        print(
            "Channel rich message failed:",
            str(e),
        )

        raise


async def send_article(
    env,
    chat_id,
    article_url,
    publish_channel=False,
    on_article_ready=None,
):

    article = await fetch_article(
        article_url
    )

    article_html = clean_article(
        article["html"],
        article["url"],
    )

    rich_html = build_rich_article(
        article_html
    )

    preview = build_preview(
        article["title"],
        article["url"],
        article["teaser"],
    )

    if on_article_ready:

        await on_article_ready(
            article
        )

    hero_photo = None

    if article["hero_image"]:

        try:

            hero_photo = await _download_image(
                article["hero_image"]
            )

        except Exception as e:

            print(
                "Hero image download failed:",
                str(e),
            )

    photo_result = None

    if hero_photo:

        try:

            photo_result = await send_photo(
                env,
                chat_id,
                hero_photo,
                preview,
            )

            print(
                "Private hero image uploaded"
            )

        except Exception as e:

            print(
                "Private image upload failed:",
                str(e),
            )

    private_reply_id = None
    reusable_photo = hero_photo

    if photo_result:

        private_reply_id = (
            photo_result["result"]
            ["message_id"]
        )

        reusable_photo = (
            photo_result["result"]
            .get("photo", [{}])[-1]
            .get("file_id")
            or hero_photo
        )

    if publish_channel:

        print(
            "Publishing article to channel"
        )

        try:

            await send_channel_article(
                env,
                preview,
                rich_html,
                reusable_photo,
            )

        except Exception as e:

            print(
                "Channel publishing failed:",
                str(e),
            )

    await send_rich_message(
        env,
        chat_id,
        rich_html,
        private_reply_id,
    )

    return article
