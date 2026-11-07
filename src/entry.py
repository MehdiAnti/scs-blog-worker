import json
import time

from workers import (
    WorkerEntrypoint,
    Response,
)

from checker import (
    run_check,
)

from commands import (
    handle_command,
)

from config import (
    get_allowed_user,
)


UPDATE_TTL = 604800


class Default(WorkerEntrypoint):

    async def fetch(
        self,
        request,
    ):

        url = str(
            request.url
        )

        method = request.method

        if (
            method == "GET"
            and url.endswith("/")
        ):

            return Response(
                "OK",
                status=200,
            )

        if (
            method == "GET"
            and url.endswith("/health")
        ):

            return Response.json(
                {
                    "ok": True,
                    "service":
                        "scs-blog-worker",
                }
            )

        if (
            method == "GET"
            and url.endswith("/check")
        ):

            try:

                result = await run_check(
                    self.env
                )

                return Response.json(
                    result,
                    status=200,
                )

            except Exception as e:

                print(
                    "Manual check failed:",
                    str(e),
                )

                return Response.json(
                    {
                        "error": str(e),
                    },
                    status=500,
                )

        if (
            method == "POST"
            and url.endswith("/webhook")
        ):

            return await self._webhook(
                request
            )

        return Response(
            "Not Found",
            status=404,
        )

    async def _webhook(
        self,
        request,
    ):

        started = time.perf_counter()

        try:

            update = await request.json()

        except Exception as e:

            print(
                "Invalid webhook JSON:",
                str(e),
            )

            return Response.json(
                {
                    "ok": True,
                }
            )

        update_id = update.get(
            "update_id"
        )

        if update_id is not None:

            update_key = (
                f"telegram_update_{update_id}"
            )

            try:

                existing = await self.env.KV_BINDING.get(
                    update_key
                )

                if existing:

                    print(
                        f"Duplicate update ignored: {update_id}"
                    )

                    return Response.json(
                        {
                            "ok": True,
                            "duplicate": True,
                        }
                    )

            except Exception as e:

                print(
                    "Update deduplication read failed:",
                    str(e),
                )

        message = (
            update.get("message")
            or update.get(
                "edited_message"
            )
            or {}
        )

        chat = (
            message.get("chat")
            or {}
        )

        chat_id = chat.get(
            "id"
        )

        if chat_id is None:

            return Response.json(
                {
                    "ok": True,
                }
            )

        if (
            int(chat_id)
            != get_allowed_user(
                self.env
            )
        ):

            return Response.json(
                {
                    "ok": True,
                }
            )

        text = (
            message.get(
                "text",
                "",
            )
            .strip()
        )

        if not text:

            return Response.json(
                {
                    "ok": True,
                }
            )

        try:

            print(
                f"Webhook command started | "
                f"Update={update_id} | "
                f"Command={text.split()[0]}"
            )

            await handle_command(
                self.env,
                chat_id,
                text,
            )

            if update_id is not None:

                await self.env.KV_BINDING.put(
                    update_key,
                    "1",
                    expiration_ttl=UPDATE_TTL,
                )

            elapsed = (
                time.perf_counter()
                - started
            )

            print(
                f"Webhook command completed | "
                f"Update={update_id} | "
                f"Duration={elapsed:.3f}s"
            )

        except Exception as e:

            print(
                f"Webhook command failed | "
                f"Update={update_id} | "
                f"Error={str(e)}"
            )

            raise

        return Response.json(
            {
                "ok": True,
            }
        )

    async def scheduled(
        self,
        controller,
        env,
        ctx,
    ):

        print(
            f"Cron started: "
            f"{controller.cron}"
        )

        started = time.perf_counter()

        try:

            result = await run_check(
                self.env
            )

            elapsed = (
                time.perf_counter()
                - started
            )

            print(
                f"Cron result: {result} | "
                f"Duration={elapsed:.3f}s"
            )

        except Exception as e:

            print(
                "Cron failed:",
                str(e),
            )

            raise
