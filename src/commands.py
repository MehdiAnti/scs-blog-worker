from config import (
    get_allowed_user,
)

from storage import (
    get_last_article,
    get_status,
    save_detected,
)

from telegram import (
    send_message,
    send_article,
)

from checker import (
    run_check,
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
        f"Title:\n"
        f"{article.get('title', '')}\n\n"

        f"URL:\n"
        f"{article.get('url', '')}"
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
        f"{status['last_result']}\n"

        f"<b>Last Check:</b> "
        f"{status['last_check']}\n\n"

        f"<b>Latest Article:</b>\n"
        f"{status['latest_title']}\n"
        f"{status['latest_url']}\n\n"

        f"<b>Last Error:</b>\n"
        f"{status['last_error'] or 'None'}"
    )

    await send_message(
        env,
        chat_id,
        text,
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
            f"{article['title']}"
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
                f"{result['title']}"
            ),
        )

    except Exception as e:

        await send_message(
            env,
            chat_id,
            f"❌ {e}",
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

    elif text.startswith(
        "/preview "
    ):

        await cmd_preview(
            env,
            chat_id,
            text,
        )

    elif text.startswith(
        "/publish "
    ):

        await cmd_publish(
            env,
            chat_id,
            text,
        )
