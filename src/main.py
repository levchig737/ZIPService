import logging
from logging import getLogger

import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware


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

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
