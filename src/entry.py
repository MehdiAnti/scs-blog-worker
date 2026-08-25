import json

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


class Default(WorkerEntrypoint):

    async def fetch(
        self,
        request,
    ):

        url = str(
            request.url
        )

        method = request.method

        # Health

        if (
            method == "GET"
            and url.endswith("/")
        ):

            return Response(
                "OK",
                status=200,
            )

        # Health endpoint

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

        # Manual check

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

                return Response.json(
                    {
                        "error": str(e),
                    },
                    status=500,
                )

        # Telegram webhook

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

        try:

            update = (
                await request.json()
            )

        except Exception:

            return Response.json(
                {
                    "ok": True,
                }
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

            await handle_command(
                self.env,
                chat_id,
                text,
            )

        except Exception as e:

            print(
                "Command error:",
                e,
            )

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

        try:

            result = await run_check(
                self.env
            )

            print(
                "Cron result:",
                result,
            )

        except Exception as e:

            print(
                "Cron failed:",
                e,
            )

            # Re-raise so the scheduled
            # invocation is recorded as failed.

            raise
