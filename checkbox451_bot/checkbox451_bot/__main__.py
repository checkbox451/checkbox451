import logging

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    from . import auth, goods, handlers, kbd

    auth.init()
    goods.init()
    kbd.init()

    handlers.start_polling()
