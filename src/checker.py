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
    print("Check started")

    status = await get_status(
        env
    )

    try:
        print("Fetching latest blog post")

        latest = await get_latest_post()

        print(
            f"Latest post found | "
            f"Title={latest['title']} | "
            f"URL={latest['url']}"
        )

        status["last_check"] = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
        )

        print("Checking article history")

        if not await article_is_new(
            env,
            latest["url"],
        ):
            print("No new article")

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

        print("New article detected")

        article = await send_article(
            env,
            get_allowed_user(env),
            latest["url"],
            publish_channel=True,
        )

        print(
            "Telegram publishing completed"
        )

        await save_detected(
            env,
            article["url"],
            article["title"],
        )

        print(
            "Article saved to detected storage"
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

        print("Check completed successfully")

        return {
            "status": "posted",
            "url": article["url"],
            "title": article["title"],
        }

    except Exception as e:
        print(
            "Check failed:",
            repr(e),
        )

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
                repr(status_error),
            )

        raise
