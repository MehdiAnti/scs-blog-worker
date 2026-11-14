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
        url = str(request.url)
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
                    "service": "scs-blog-worker",
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
                    e,
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
        try:
            update = await request.json()

        except Exception as e:
            print(
                "Webhook JSON error:",
                e,
            )

            return Response.json(
                {
                    "ok": True,
                }
            )

        message = (
            update.get("message")
            or update.get("edited_message")
            or {}
        )

        chat = (
            message.get("chat")
            or {}
        )

        chat_id = chat.get("id")

        if chat_id is None:
            return Response.json(
                {
                    "ok": True,
                }
            )

        try:
            if (
                int(chat_id)
                != get_allowed_user(self.env)
            ):
                return Response.json(
                    {
                        "ok": True,
                    }
                )

        except Exception as e:
            print(
                "Webhook authorization error:",
                e,
            )

            return Response.json(
                {
                    "ok": True,
                }
            )

        command_text = (
            message.get("text", "")
            .strip()
        )

        if not command_text:
            return Response.json(
                {
                    "ok": True,
                }
            )

        print(
            f"Webhook accepted | "
            f"Command={command_text.split()[0]}"
        )

        self.ctx.waitUntil(
            self._process_command(
                chat_id,
                command_text,
            )
        )

        return Response.json(
            {
                "ok": True,
            }
        )

    async def _process_command(
        self,
        chat_id,
        command_text,
    ):
        try:
            print(
                f"Background command started | "
                f"Command={command_text.split()[0]}"
            )

            await handle_command(
                self.env,
                chat_id,
                command_text,
            )

            print(
                "Background command completed"
            )

        except Exception as e:
            print(
                "Background command failed:",
                repr(e),
            )

    async def scheduled(
        self,
        controller,
        env,
        ctx,
    ):
        print(
            f"Cron started: {controller.cron}"
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
                repr(e),
            )

            raise
