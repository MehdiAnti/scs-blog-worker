BLOG_URL = "https://blog.scssoft.com"

RSS_URL = "https://feeds.feedburner.com/ScsSoftwaresBlog"

USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

LATEST_ARTICLE_KEY = "latest_article"
STATUS_KEY = "status"
PUBLISH_SETTINGS_KEY = "publishing_settings"

CRON = "*/5 * * * *"


def get_bot_token(env):
    token = getattr(env, "BOT_TOKEN", None)

    if not token:
        raise RuntimeError("BOT_TOKEN is not configured")

    return token


def get_allowed_users(env):
    value = getattr(env, "ALLOWED_USER", None)

    if not value:
        raise RuntimeError("ALLOWED_USER is not configured")

    try:
        users = {
            int(user_id.strip())
            for user_id in str(value).split(",")
            if user_id.strip()
        }

    except ValueError:
        raise RuntimeError(
            "ALLOWED_USER must contain valid numeric IDs separated by commas"
        )

    if not users or any(user_id <= 0 for user_id in users):
        raise RuntimeError(
            "ALLOWED_USER must contain valid positive Telegram user IDs"
        )

    return users


def get_channel_id(env):
    value = getattr(env, "CHANNEL_ID", None)

    if value is None:
        raise RuntimeError("CHANNEL_ID is not configured")

    return str(value)


def get_post_to_channel(env):
    value = getattr(env, "POST_TO_CHANNEL", "false")

    return str(value).lower() == "true"


def get_send_to_admin(env):
    value = getattr(env, "SEND_TO_ADMIN", "true")

    return str(value).lower() == "true"
