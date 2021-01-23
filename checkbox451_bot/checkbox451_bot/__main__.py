import logging

from checkbox451_bot import auth, goods, handlers, kbd

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    auth.init()
    goods.init()
    kbd.init()

    handlers.start_polling()
