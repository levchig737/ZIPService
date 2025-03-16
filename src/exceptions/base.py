from typing import Optional


class BaseExceptionWithMessage(Exception):
    status_code: int
    message: str

    def __init__(self, message: str = None, status_code: Optional[int] = None):
        self.message = message or self.message
        self.status_code = status_code or self.status_code
        super().__init__(self.message)
