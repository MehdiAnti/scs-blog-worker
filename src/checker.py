from datetime import (
    datetime,
    timezone,
)

from blogger import (
    get_latest_post,
)

from storage import (
    article_is_new,
    save_detected,
    get_status,
    save_status,
)

from telegram import (
    send_article,
)

from config import (
    get_allowed_user,
)


def _utc_now():

    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )


async def run_check(env):

    status = await get_status(
        env
    )

    status["last_check"] = _utc_now()

    try:

        latest = await get_latest_post()

        print(
            f"Latest article: {latest['title']} | "
            f"{latest['url']}"
        )

        if not await article_is_new(
            env,
            latest["url"],
        ):

            status["last_result"] = (
                "no_new_article"
            )

            status["last_error"] = ""

            await save_status(
                env,
                status,
            )

            return {
                "status": "no_new_article",
            }

        async def mark_article_ready(article):

            await save_detected(
                env,
                article["url"],
                article["title"],
            )

            print(
                f"Article marked as detected: "
                f"{article['url']}"
            )

        article = await send_article(
            env,
            get_allowed_user(env),
            latest["url"],
            publish_channel=True,
            on_article_ready=mark_article_ready,
        )

        status["last_result"] = "posted"

        status["latest_title"] = (
            article["title"]
        )

        status["latest_url"] = (
            article["url"]
        )

        status["last_error"] = ""

        await save_status(
            env,
            status,
        )

        return {
            "status": "posted",
            "url": article["url"],
            "title": article["title"],
        }

    except Exception as e:

        status["last_result"] = "failed"

        status["last_error"] = str(e)

        try:

            await save_status(
                env,
                status,
            )

        except Exception as status_error:

            print(
                "Failed to save status:",
                str(status_error),
            )

        print(
            "Check failed:",
            str(e),
        )

        raise
