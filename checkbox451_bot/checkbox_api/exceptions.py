class CheckboxAPIError(Exception):
    pass


class CheckboxSignError(CheckboxAPIError):
    pass


class CheckboxReceiptError(CheckboxAPIError):
    pass


class CheckboxShiftError(CheckboxAPIError):
    pass
