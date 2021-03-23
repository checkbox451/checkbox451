import os
from logging import getLogger

import gspread_asyncio
from google.oauth2.service_account import Credentials

service_account_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
spreadsheet_key = os.environ.get("GOOGLE_SPREADSHEET_KEY")

log = getLogger(__name__)


def get_creds():
    creds = Credentials.from_service_account_file(service_account_file)
    scoped = creds.with_scopes(
        [
            "https://www.googleapis.com/auth/spreadsheets",
        ]
    )
    return scoped


async def append_row(row, worksheet_title):
    if not manager:
        return

    if not spreadsheet_key:
        log.warning("missing spreadsheet key; ignoring...")
        return

    if not worksheet_title:
        log.warning("missing worksheet title; ignoring...")
        return

    client = await manager.authorize()
    spreadsheet = await client.open_by_key(spreadsheet_key)
    wks = await spreadsheet.worksheet(worksheet_title)

    await wks.append_row(row, value_input_option="USER_ENTERED")


def init():
    if not service_account_file:
        log.warning("missing service account file; ignoring...")
        return

    return gspread_asyncio.AsyncioGspreadClientManager(get_creds)


manager = init()
