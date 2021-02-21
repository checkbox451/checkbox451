import logging

logging.basicConfig(level=logging.INFO)

from checkbox451_bot import auth, goods, handlers, kbd

auth.init()
goods.init()
kbd.init()

handlers.start_polling()
