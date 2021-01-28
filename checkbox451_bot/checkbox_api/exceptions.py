class CheckboxAPIError(Exception):
    pass


class CheckboxReceiptError(CheckboxAPIError):
    pass


class CheckboxShiftError(CheckboxAPIError):
    pass
