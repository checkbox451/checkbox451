import os

import gspread_asyncio
from google.oauth2.service_account import Credentials

service_account_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
spreadsheet_key = os.environ.get("GOOGLE_SPREADSHEET_KEY")


def get_creds():
    creds = Credentials.from_service_account_file(service_account_file)
    scoped = creds.with_scopes(
        [
            "https://www.googleapis.com/auth/spreadsheets",
        ]
    )
    return scoped


manager = gspread_asyncio.AsyncioGspreadClientManager(get_creds)


async def append_row(row, worksheet_title):
    if service_account_file is None:
        return

    client = await manager.authorize()
    spreadsheet = await client.open_by_key(spreadsheet_key)
    wks = await spreadsheet.worksheet(worksheet_title)

    await wks.append_row(row, value_input_option="USER_ENTERED")
