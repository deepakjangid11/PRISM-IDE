from typing import Any


def error_message_detail(error: Exception, error_detail: Any) -> str:
    _, _, exc_tb = error_detail.exc_info()

    file_name = exc_tb.tb_frame.f_code.co_filename
    line_number = exc_tb.tb_lineno

    error_message = (
        f"Error occurred in python script name "
        f"[{file_name}] line number [{line_number}] "
        f"error message [{str(error)}]"
    )

    return error_message


class CustomException(Exception):
    def __init__(self, error_message: Exception, error_detail: Any) -> None:
        super().__init__(error_message)
        self.error_message = error_message_detail(
            error_message,
            error_detail,
        )

    def __str__(self) -> str:
        return self.error_message