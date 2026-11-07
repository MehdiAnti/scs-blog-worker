import html
import time

from storage import (
    get_last_article,
    get_status,
    save_detected,
)

from telegram import (
    send_message,
    send_article,
)

from blogger import (
    fetch_article,
    probe_image,
)

from html_build import (
    clean_article,
    build_rich_article,
)

from checker import (
    run_check,
)


def _safe(value):

    return html.escape(
        str(value or "")
    )


async def cmd_start(
    env,
    chat_id,
):

    await send_message(
        env,
        chat_id,
        (
            "<b>SCS Blog Telegram Bot</b>\n\n"
            "<b>Commands</b>\n"
            "/last - Last stored article\n"
            "/status - Bot status\n"
            "/checknow - Check immediately\n"
            "/rich URL - Rich article debug\n"
            "/preview URL - Preview article\n"
            "/publish URL - Publish article"
        ),
    )


async def cmd_last(
    env,
    chat_id,
):

    article = await get_last_article(
        env
    )

    text = (
        f"<b>Title:</b>\n"
        f"{_safe(article.get('title'))}\n\n"
        f"<b>URL:</b>\n"
        f"{_safe(article.get('url'))}"
    )

    await send_message(
        env,
        chat_id,
        text,
    )


async def cmd_status(
    env,
    chat_id,
):

    status = await get_status(
        env
    )

    text = (
        "<b>📊 Bot Status</b>\n\n"
        f"<b>Last Result:</b> "
        f"{_safe(status['last_result'])}\n"
        f"<b>Last Check:</b> "
        f"{_safe(status['last_check'])}\n\n"
        f"<b>Latest Article:</b>\n"
        f"{_safe(status['latest_title'])}\n"
        f"{_safe(status['latest_url'])}\n\n"
        f"<b>Last Error:</b>\n"
        f"{_safe(status['last_error'] or 'None')}"
    )

    await send_message(
        env,
        chat_id,
        text,
    )


async def cmd_rich(
    env,
    chat_id,
    text,
):

    parts = text.split(
        " ",
        1,
    )

    if len(parts) != 2:

        await send_message(
            env,
            chat_id,
            "Usage:\n/rich ARTICLE_URL",
        )

        return

    article_url = parts[1].strip()

    started = time.perf_counter()

    try:

        article = await fetch_article(
            article_url
        )

        fetch_duration = (
            time.perf_counter()
            - started
        )

        image_result = await probe_image(
            article["hero_image"]
        )

        clean_started = time.perf_counter()

        article_html = clean_article(
            article["html"],
            article["url"],
        )

        clean_duration = (
            time.perf_counter()
            - clean_started
        )

        rich_started = time.perf_counter()

        rich_html = build_rich_article(
            article_html
        )

        rich_duration = (
            time.perf_counter()
            - rich_started
        )

        total_duration = (
            time.perf_counter()
            - started
        )

        image_error = (
            image_result.get("error")
            or "None"
        )

        final_url = image_result.get(
            "final_url",
            article["hero_image"] or "",
        )

        debug_info = (
            "<b>🔬 Rich Debug Report</b>\n\n"

            f"<b>Title:</b>\n"
            f"{_safe(article['title'])}\n\n"

            f"<b>Article URL:</b>\n"
            f"{_safe(article['url'])}\n\n"

            "<b>HTML Information</b>\n"
            f"Original HTML: "
            f"{article.get('original_html_length', 0)} chars\n"
            f"HTML elements: "
            f"{article.get('element_count', 0)}\n"
            f"Cleaned HTML: "
            f"{len(article_html)} chars\n"
            f"Rich HTML: "
            f"{len(rich_html)} chars\n\n"

            "<b>Image Information</b>\n"
            f"Hero URL:\n"
            f"{_safe(article['hero_image'])}\n\n"
            f"Final URL:\n"
            f"{_safe(final_url)}\n"
            f"HTTP status: "
            f"{_safe(image_result.get('status'))}\n"
            f"Content-Type: "
            f"{_safe(image_result.get('content_type'))}\n"
            f"Content-Length: "
            f"{_safe(image_result.get('size'))}\n"
            f"Image error: "
            f"{_safe(image_error)}\n\n"

            "<b>Processing Time</b>\n"
            f"Article fetch: "
            f"{fetch_duration:.3f}s\n"
            f"HTML cleaning: "
            f"{clean_duration:.3f}s\n"
            f"Rich generation: "
            f"{rich_duration:.3f}s\n"
            f"Total: "
            f"{total_duration:.3f}s"
        )

        await send_message(
            env,
            chat_id,
            debug_info,
        )

        await send_message(
            env,
            chat_id,
            "<b>Generated Rich HTML</b>",
        )

        chunk_size = 3000

        for i in range(
            0,
            len(article_html),
            chunk_size,
        ):

            chunk = article_html[
                i:i + chunk_size
            ]

            escaped_chunk = html.escape(
                chunk
            )

            await send_message(
                env,
                chat_id,
                f"<pre>{escaped_chunk}</pre>",
            )

        await send_message(
            env,
            chat_id,
            (
                "<b>Rich Debug Completed</b>\n"
                "No article was published."
            ),
        )

    except Exception as e:

        print(
            "Rich debug failed:",
            str(e),
        )

        await send_message(
            env,
            chat_id,
            (
                "❌ <b>Rich Debug Failed</b>\n\n"
                f"<code>{_safe(e)}</code>"
            ),
        )


async def cmd_preview(
    env,
    chat_id,
    text,
):

    parts = text.split(
        " ",
        1,
    )

    if len(parts) != 2:

        await send_message(
            env,
            chat_id,
            "Usage:\n/preview ARTICLE_URL",
        )

        return

    article_url = parts[1].strip()

    await send_article(
        env,
        chat_id,
        article_url,
        publish_channel=False,
    )


async def cmd_publish(
    env,
    chat_id,
    text,
):

    parts = text.split(
        " ",
        1,
    )

    if len(parts) != 2:

        await send_message(
            env,
            chat_id,
            "Usage:\n/publish ARTICLE_URL",
        )

        return

    article_url = parts[1].strip()

    article = await send_article(
        env,
        chat_id,
        article_url,
        publish_channel=True,
    )

    await save_detected(
        env,
        article["url"],
        article["title"],
    )

    await send_message(
        env,
        chat_id,
        (
            "✅ Published.\n\n"
            f"{_safe(article['title'])}"
        ),
    )


async def cmd_checknow(
    env,
    chat_id,
):

    try:

        result = await run_check(
            env
        )

        if (
            result["status"]
            == "no_new_article"
        ):

            await send_message(
                env,
                chat_id,
                "ℹ️ No new article found.",
            )

            return

        await send_message(
            env,
            chat_id,
            (
                "✅ Published successfully.\n\n"
                f"{_safe(result['title'])}"
            ),
        )

    except Exception as e:

        await send_message(
            env,
            chat_id,
            (
                "❌ <b>Check failed</b>\n\n"
                f"<code>{_safe(e)}</code>"
            ),
        )


async def handle_command(
    env,
    chat_id,
    text,
):

    if text == "/start":

        await cmd_start(
            env,
            chat_id,
        )

    elif text == "/last":

        await cmd_last(
            env,
            chat_id,
        )

    elif text == "/status":

        await cmd_status(
            env,
            chat_id,
        )

    elif text == "/checknow":

        await cmd_checknow(
            env,
            chat_id,
        )

    elif text.startswith("/rich "):

        await cmd_rich(
            env,
            chat_id,
            text,
        )

    elif text.startswith("/preview "):

        await cmd_preview(
            env,
            chat_id,
            text,
        )

    elif text.startswith("/publish "):

        await cmd_publish(
            env,
            chat_id,
            text,
        )
