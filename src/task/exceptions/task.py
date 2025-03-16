from starlette import status
from exceptions import BaseExceptionWithMessage


class InvalidFileException(BaseExceptionWithMessage):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Недопустимый файл"


class FileSizeExceededException(BaseExceptionWithMessage):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Размер файла превышает 100 МБ"


class ZipValidationException(BaseExceptionWithMessage):
    status_code = status.HTTP_400_BAD_REQUEST
    message = "Ошибка валидации ZIP-архива"


class TaskNotFoundException(BaseExceptionWithMessage):
    status_code = status.HTTP_404_NOT_FOUND
    message = "Задача не найдена"


class ProcessingException(BaseExceptionWithMessage):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Ошибка обработки задачи"


class AccessDeniedException(BaseExceptionWithMessage):
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Invalid authentication credentials"
