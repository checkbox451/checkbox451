import asyncio
import os
from contextlib import asynccontextmanager
from datetime import date

import pygsheets

from checkbox451_bot import auth, bot, checkbox_api, handlers

service_account_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
spreadsheet_key = os.environ.get("GOOGLE_SPREADSHEET_KEY")
worksheet_title = os.environ.get("GOOGLE_WORKSHEET_TITLE")


async def error(msg):
    await handlers.helpers.broadcast(
        None,
        auth.ADMIN,
        handlers.helpers.error,
        msg,
    )


@asynccontextmanager
async def bot_init():
    bot.init()
    try:
        yield
    finally:
        await bot.obj.session.close()


async def main():
    if await checkbox_api.shift.shift_balance() is None:
        print("shift is closed")
        return

    async with bot_init():
        try:
            income = await checkbox_api.shift.shift_close()
        except Exception as e:
            await error(str(e))
            print(f"shift close failed: {e!s}")
            return

        today = date.today().isoformat()
        print(f"{today}: shift closed: income {income:.02f}")

        if income and service_account_file:
            try:
                client = pygsheets.authorize(
                    service_account_file=service_account_file
                )
                spreadsheet = client.open_by_key(spreadsheet_key)
                wks = spreadsheet.worksheet_by_title(worksheet_title)
                wks.append_table([[today, income]])
            except Exception as e:
                await error(str(e))
                print(f"shift reporting failed: {e!s}")
                return

        await handlers.helpers.broadcast(
            None,
            auth.SUPERVISOR,
            bot.obj.send_message,
            f"Дохід {income:.02f} грн",
        )


if __name__ == "__main__":
    asyncio.run(main())
