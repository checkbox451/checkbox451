import asyncio
import os
import sys
from datetime import date

import pygsheets
from pygsheets import Worksheet

from checkbox451_bot import checkbox_api

service_account_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
spreadsheet_key = os.environ.get("GOOGLE_SPREADSHEET_KEY")
worksheet_title = os.environ.get("GOOGLE_WORKSHEET_TITLE")


async def main():
    if await checkbox_api.shift.shift_balance() is None:
        sys.exit("shift is closed")

    today = date.today()
    income = await checkbox_api.shift.shift_close()
    print(f"{today}: shift closed: income {income:.02f}")

    if income and service_account_file:
        client = pygsheets.authorize(service_account_file=service_account_file)
        spreadsheet = client.open_by_key(spreadsheet_key)
        wks: Worksheet = spreadsheet.worksheet_by_title(worksheet_title)
        wks.append_table([[today.isoformat(), income]])


asyncio.run(main())
