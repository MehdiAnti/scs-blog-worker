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


async def run_check(env):

    status = await get_status(
        env
    )

    try:

        latest = await get_latest_post()

        status["last_check"] = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
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
                "status":
                    "no_new_article",
            }

        article = await send_article(
            env,
            get_allowed_user(env),
            latest["url"],
            publish_channel=True,
        )

        # Only save AFTER all Telegram
        # publishing succeeded.

        await save_detected(
            env,
            article["url"],
            article["title"],
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
                status_error,
            )

        raise
