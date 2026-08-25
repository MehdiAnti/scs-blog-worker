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

CRON = "*/5 * * * *"


def get_bot_token(env):
    token = getattr(env, "BOT_TOKEN", None)

    if not token:
        raise RuntimeError("BOT_TOKEN is not configured")

    return token


def get_allowed_user(env):
    value = getattr(env, "ALLOWED_USER", None)

    if value is None:
        raise RuntimeError("ALLOWED_USER is not configured")

    return int(value)


def get_channel_id(env):
    value = getattr(env, "CHANNEL_ID", None)

    if value is None:
        raise RuntimeError("CHANNEL_ID is not configured")

    return str(value)


def get_post_to_channel(env):
    value = getattr(env, "POST_TO_CHANNEL", "false")

    return str(value).lower() == "true"
