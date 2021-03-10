import asyncio
import logging

fmt = (
    "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - "
    "%(message)s"
)
logging.basicConfig(format=fmt, level=logging.INFO)

from checkbox451_bot import auth, goods, handlers, kbd, pb2gsheet, shift_close

auth.init()
goods.init()
kbd.init()

loop = asyncio.get_event_loop()
loop.create_task(pb2gsheet.run())
loop.create_task(shift_close.scheduler())

handlers.start_polling()
