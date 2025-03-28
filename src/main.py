import logging
from logging import getLogger

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from api.api import router as api_router
from base.lifespan import lifespan
from task.api.api import router as task_router
from task.exceptions.task_middleware import (
    exception_traceback_middleware as task_exception_traceback_middleware,
)

origins = [
    "*",
]

logger = getLogger("api")
logging.basicConfig()
logger.setLevel(logging.DEBUG)

app = FastAPI(Title="ZIPService", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(task_router)

app.middleware("http")(task_exception_traceback_middleware)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
