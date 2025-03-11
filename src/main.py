import logging
from logging import getLogger

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from api.api import router as api_router

from exceptions.base import exception_traceback_middleware

origins = [
    "*",
]

logger = getLogger("api")
logging.basicConfig()
logger.setLevel(logging.DEBUG)

app = FastAPI(
    Title="TestWA",
)

app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(exception_traceback_middleware)
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
