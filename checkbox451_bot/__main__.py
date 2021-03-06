import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from checkbox451_bot import auth, goods, handlers, kbd, shift_close

auth.init()
goods.init()
kbd.init()

asyncio.get_event_loop().create_task(shift_close.scheduler())
handlers.start_polling()
