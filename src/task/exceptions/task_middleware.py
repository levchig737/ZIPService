from logging import getLogger
from typing import Callable

from fastapi.requests import Request
from starlette import status
from starlette.responses import JSONResponse, Response

from task.exceptions import (
    InvalidFileException,
    FileSizeExceededException,
    ZipValidationException,
    TaskNotFoundException,
    ProcessingException,
    AccessDeniedException
)

logger = getLogger("api")


async def exception_traceback_middleware(
    request: Request, call_next: Callable
) -> Response:
    try:
        response: Response = await call_next(request)
    except InvalidFileException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.message},
        )
    except FileSizeExceededException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.message},
        )
    except ZipValidationException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.message},
        )
    except TaskNotFoundException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.message},
        )
    except ProcessingException as e:
        logger.error(f"Processing error: {e.message}")
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.message},
        )
    except AccessDeniedException as e:
        logger.error(f"AccessDeniedException: {e.message}")
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.message},
        )
    except Exception as e:
        logger.exception("%s: %s", e.__class__.__name__, e)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={}
        )
    else:
        return response
