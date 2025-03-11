from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    username: str
    description: str | None
    role_id: int


class UserCreate(schemas.BaseUserCreate):
    username: str


class UserUpdate(schemas.BaseUserUpdate):
    username: str
    description: str | None
