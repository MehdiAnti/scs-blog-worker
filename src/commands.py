import html

from config import (
    get_allowed_user,
)

from storage import (
    get_last_article,
    get_status,
    save_detected,
    get_publish_settings,
    save_publish_settings,
)

from telegram import (
    send_message,
    send_article,
    edit_message_text,
    answer_callback_query,
)

from blogger import (
    fetch_article,
)

from html_build import (
    clean_article,
)

from checker import (
    run_check,
)


MAIN_MENU_TEXT = (
    "<b>SCS Blog Telegram Bot</b>\n\n"
    "<b>Commands</b>\n"
    "/last - Last stored article\n"
    "/status - Bot status\n"
    "/checknow - Check immediately\n"
    "/settings - Publishing settings\n"
    "/rich URL - Debug cleaned HTML\n"
    "/preview URL - Preview article\n"
    "/publish URL - Publish article"
)


def _settings_keyboard(settings):
    channel_text = (
        "🟢 Channel: ON"
        if settings["post_to_channel"]
        else "🔴 Channel: OFF"
    )

    admin_text = (
        "🟢 Admin: ON"
        if settings["send_to_admin"]
        else "🔴 Admin: OFF"
    )

    return {
        "inline_keyboard": [
            [
                {
                    "text": channel_text,
                    "callback_data": "settings:channel",
                }
            ],
            [
                {
                    "text": admin_text,
                    "callback_data": "settings:admin",
                }
            ],
            [
                {
                    "text": "⬅️ Back",
                    "callback_data": "menu:back",
                }
            ],
        ]
    }


def _settings_text(settings):
    return (
        "<b>⚙️ Publishing Settings</b>\n\n"
        f"Channel publishing: "
        f"<b>{'ON' if settings['post_to_channel'] else 'OFF'}</b>\n"
        f"Admin publishing: "
        f"<b>{'ON' if settings['send_to_admin'] else 'OFF'}</b>\n\n"
        "Tap a button to change its state. "
        "Changes are saved automatically."
    )


async def _show_settings(
    env,
    chat_id,
    message_id=None,
):
    settings = await get_publish_settings(env)

    text = _settings_text(settings)
    keyboard = _settings_keyboard(settings)

    if message_id is None:
        return await send_message(
            env,
            chat_id,
            text,
            reply_markup=keyboard,
        )

    return await edit_message_text(
        env,
        chat_id,
        message_id,
        text,
        reply_markup=keyboard,
    )


async def cmd_settings(
    env,
    chat_id,
):
    await _show_settings(
        env,
        chat_id,
    )


async def handle_callback(
    env,
    callback_query,
):
    callback_id = callback_query.get("id")
    callback_data = callback_query.get("data", "")

    message = callback_query.get("message") or {}
    chat = message.get("chat") or {}

    chat_id = chat.get("id")
    message_id = message.get("message_id")

    if not callback_id:
        return

    if chat_id is None or message_id is None:
        await answer_callback_query(
            env,
            callback_id,
            "This button is no longer available.",
        )
        return

    if callback_data == "menu:settings":
        await answer_callback_query(
            env,
            callback_id,
        )

        await _show_settings(
            env,
            chat_id,
            message_id,
        )
        return

    if callback_data == "menu:back":
        await answer_callback_query(
            env,
            callback_id,
        )

        await edit_message_text(
            env,
            chat_id,
            message_id,
            MAIN_MENU_TEXT,
            reply_markup={
                "inline_keyboard": []
            },
        )
        return

    setting_keys = {
        "settings:channel": "post_to_channel",
        "settings:admin": "send_to_admin",
    }

    setting_key = setting_keys.get(
        callback_data
    )

    if setting_key is None:
        await answer_callback_query(
            env,
            callback_id,
            "Unknown action.",
        )
        return

    settings = await get_publish_settings(env)

    settings[setting_key] = not settings[setting_key]

    await save_publish_settings(
        env,
        settings,
    )

    await answer_callback_query(
        env,
        callback_id,
        "Setting updated.",
    )

    await _show_settings(
        env,
        chat_id,
        message_id,
    )


async def cmd_start(
    env,
    chat_id,
):
    await send_message(
        env,
        chat_id,
        MAIN_MENU_TEXT,
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

    try:
        article = await fetch_article(
            article_url
        )

        article_html = clean_article(
            article["html"]
        )

        debug_html = html.escape(
            article_html
        )

        chunk_size = 4000

        for i in range(
            0,
            len(debug_html),
            chunk_size,
        ):
            chunk = debug_html[
                i:i + chunk_size
            ]

            await send_message(
                env,
                chat_id,
                f"<pre>{chunk}</pre>",
            )

    except Exception as e:
        await send_message(
            env,
            chat_id,
            f"❌ {e}",
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
        publish_admin=True,
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

    settings = await get_publish_settings(env)

    if not (
        settings["send_to_admin"]
        or settings["post_to_channel"]
    ):
        await send_message(
            env,
            chat_id,
            "⏸ Publishing is disabled for both destinations. "
            "Enable at least one in /settings.",
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

        if result["status"] == "no_new_article":
            await send_message(
                env,
                chat_id,
                "ℹ️ No new article found.",
            )
            return

        if result["status"] == "publishing_disabled":
            await send_message(
                env,
                chat_id,
                "⏸ Publishing is disabled for both destinations. "
                "Enable Channel or Admin in /settings.",
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

    elif text == "/settings":
        await cmd_settings(
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
