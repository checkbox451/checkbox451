class Button(str):
    def __new__(cls, text, *alt):
        self = super().__new__(cls, text)
        self.__all_texts = (text, *alt)
        return self

    def __eq__(self, other):
        return other in self.__all_texts


btn_auth = Button("👤 Авторизуватися")
btn_receipt = Button("📜 Створити чек", "Створити чек")
btn_cancel = Button("🚫 Скасувати")
