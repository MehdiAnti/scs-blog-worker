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

    print(
        f"[TELEGRAM] {method} REQUEST STARTED"
    )

    async with httpx.AsyncClient(
        timeout=timeout
    ) as client:

        try:

            response = await client.post(
                url,
                json=payload,
            )

        except Exception as e:

            print(
                f"[TELEGRAM] {method} "
                f"NETWORK ERROR: {type(e).__name__}: {e}"
            )

            raise

    print(
        f"[TELEGRAM] {method} "
        f"HTTP STATUS: {response.status_code}"
    )

    if not response.is_success:

        print(
            f"[TELEGRAM] {method} "
            f"FAILED RESPONSE: {response.text}"
        )

        raise Exception(
            response.text
        )

    data = response.json()

    if not data.get("ok"):

        print(
            f"[TELEGRAM] {method} "
            f"TELEGRAM ERROR: {response.text}"
        )

        raise Exception(
            response.text
        )

    print(
        f"[TELEGRAM] {method} SUCCESS"
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
        timeout=60.0,
    )


async def send_photo(
    env,
    chat_id,
    photo,
    caption,
):

    print(
        "[ARTICLE] HERO IMAGE URL:",
        photo,
    )

    print(
        "[ARTICLE] SENDING HERO IMAGE BY URL"
    )

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


async def send_photo_upload(
    env,
    chat_id,
    photo_url,
    caption,
):

    print(
        "[IMAGE TEST B] DOWNLOADING IMAGE"
    )

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=60.0,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "image/*,*/*",
        },
    ) as client:

        response = await client.get(
            photo_url
        )

    print(
        "[IMAGE TEST B] DOWNLOAD STATUS:",
        response.status_code,
    )

    print(
        "[IMAGE TEST B] FINAL URL:",
        str(response.url),
    )

    print(
        "[IMAGE TEST B] CONTENT TYPE:",
        response.headers.get("content-type"),
    )

    print(
        "[IMAGE TEST B] FILE SIZE:",
        len(response.content),
    )

    print(
        "[IMAGE TEST B] FIRST 16 BYTES:",
        response.content[:16].hex(),
    )

    response.raise_for_status()

    content_type = (
        response.headers.get(
            "content-type",
            "",
        )
        .split(";")[0]
        .strip()
    )

    if not content_type.startswith("image/"):

        raise Exception(
            "Downloaded content is not an image: "
            + content_type
        )

    if not response.content:

        raise Exception(
            "Downloaded image is empty"
        )

    extension = (
        content_type.split("/")[-1]
        .replace("jpeg", "jpg")
    )

    filename = f"hero.{extension}"

    token = get_bot_token(env)

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{token}/sendPhoto"
    )

    print(
        "[IMAGE TEST B] UPLOADING IMAGE BYTES TO TELEGRAM"
    )

    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        telegram_response = await client.post(
            telegram_url,
            data={
                "chat_id": str(chat_id),
                "caption": caption,
                "parse_mode": "HTML",
            },
            files={
                "photo": (
                    filename,
                    response.content,
                    content_type,
                ),
            },
        )

    print(
        "[IMAGE TEST B] TELEGRAM HTTP STATUS:",
        telegram_response.status_code,
    )

    print(
        "[IMAGE TEST B] TELEGRAM RESPONSE:",
        telegram_response.text,
    )

    telegram_response.raise_for_status()

    data = telegram_response.json()

    if not data.get("ok"):

        raise Exception(
            telegram_response.text
        )

    print(
        "[IMAGE TEST B] UPLOAD SUCCESS"
    )

    return data


async def send_photo_ab_test(
    env,
    chat_id,
    photo_url,
    caption,
):

    result_a = None
    error_a = None

    print(
        "\n========== IMAGE A/B TEST =========="
    )

    print(
        "[IMAGE TEST] IMAGE URL:",
        photo_url,
    )

    print(
        "[IMAGE TEST A] TESTING TELEGRAM URL FETCH"
    )

    try:

        result_a = await send_photo(
            env,
            chat_id,
            photo_url,
            caption,
        )

        print(
            "[IMAGE TEST A] RESULT: SUCCESS"
        )

    except Exception as e:

        error_a = e

        print(
            "[IMAGE TEST A] RESULT: FAILED"
        )

        print(
            "[IMAGE TEST A] ERROR:",
            repr(e),
        )

    result_b = None
    error_b = None

    print(
        "[IMAGE TEST B] TESTING DIRECT IMAGE UPLOAD"
    )

    try:

        result_b = await send_photo_upload(
            env,
            chat_id,
            photo_url,
            caption,
        )

        print(
            "[IMAGE TEST B] RESULT: SUCCESS"
        )

    except Exception as e:

        error_b = e

        print(
            "[IMAGE TEST B] RESULT: FAILED"
        )

        print(
            "[IMAGE TEST B] ERROR:",
            repr(e),
        )

    print(
        "========== IMAGE A/B RESULTS =========="
    )

    print(
        "[IMAGE TEST] URL METHOD:",
        "SUCCESS" if result_a else "FAILED",
    )

    print(
        "[IMAGE TEST] UPLOAD METHOD:",
        "SUCCESS" if result_b else "FAILED",
    )

    print(
        "========== IMAGE A/B TEST COMPLETED =========="
    )

    if result_b:
        return result_b

    if result_a:
        return result_a

    raise Exception(
        "Both image methods failed. "
        f"URL method: {error_a}. "
        f"Upload method: {error_b}"
    )


async def send_rich_message(
    env,
    chat_id,
    html,
    reply_to_message_id=None,
):

    print(
        "[ARTICLE] RICH MESSAGE STARTED"
    )

    print(
        "[ARTICLE] RICH HTML LENGTH:",
        len(html),
    )

    print(
        "[ARTICLE] REPLY TO MESSAGE ID:",
        reply_to_message_id,
    )

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

    try:

        result = await _post(
            env,
            "sendRichMessage",
            payload,
            timeout=120.0,
        )

        print(
            "[ARTICLE] RICH MESSAGE SENT SUCCESSFULLY"
        )

        return result

    except Exception as e:

        print(
            "[ARTICLE] RICH MESSAGE FAILED:",
            repr(e),
        )

        raise


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

        print(
            "[CHANNEL] SENDING HERO IMAGE"
        )

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
            "[CHANNEL] HERO IMAGE MESSAGE ID:",
            reply_id,
        )

    print(
        "[CHANNEL] SENDING RICH MESSAGE"
    )

    result = await send_rich_message(
        env,
        channel_id,
        html,
        reply_id,
    )

    print(
        "[CHANNEL] ARTICLE PUBLISHED SUCCESSFULLY"
    )

    return result


async def send_article(
    env,
    chat_id,
    article_url,
    publish_channel=False,
):

    print(
        "\n========== ARTICLE PROCESS START =========="
    )

    print(
        "[ARTICLE] URL:",
        article_url,
    )

    article = await fetch_article(
        article_url
    )

    print(
        "[ARTICLE] FETCH SUCCESS:",
        article["title"],
    )

    print(
        "[ARTICLE] SELECTED HERO IMAGE:",
        article["hero_image"],
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

    print(
        "[ARTICLE] CLEANED HTML LENGTH:",
        len(article_html),
    )

    print(
        "[ARTICLE] RICH HTML LENGTH:",
        len(rich_html),
    )

    photo_result = None

    if article["hero_image"]:

        print(
            "[ARTICLE] PRIVATE CHAT IMAGE A/B TEST"
        )

        photo_result = await send_photo_ab_test(
            env,
            chat_id,
            article["hero_image"],
            preview[:1024],
        )

        print(
            "[ARTICLE] PRIVATE CHAT PHOTO RESULT:",
            photo_result,
        )

    else:

        print(
            "[ARTICLE] NO HERO IMAGE FOUND"
        )

    if publish_channel:

        print(
            "[ARTICLE] CHANNEL PUBLISHING STAGE"
        )

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

        except Exception as e:

            print(
                "[ARTICLE] PHOTO MESSAGE ID ERROR:",
                repr(e),
            )

    print(
        "[ARTICLE] PRIVATE RICH MESSAGE STAGE"
    )

    await send_rich_message(
        env,
        chat_id,
        rich_html,
        reply_id,
    )

    print(
        "========== ARTICLE PROCESS COMPLETED ==========\n"
    )

    return article
