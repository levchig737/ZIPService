from minio import Minio
from fastapi import UploadFile
from logging import getLogger
import io

logger = getLogger("api")


class StorageRepository:
    def __init__(self, minio_client: Minio, bucket_name: str):
        self.minio_client = minio_client
        self.bucket_name = bucket_name

        # Проверяем, существует ли бакет, и создаем его, если не существует
        if not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)

    async def save_file(self, file: UploadFile, file_name: str) -> None:
        file_content = await file.read()
        self.minio_client.put_object(
            self.bucket_name,
            file_name,
            io.BytesIO(file_content),
            len(file_content)
        )

    def get_file(self, file_name: str) -> bytes:
        response = self.minio_client.get_object(self.bucket_name, file_name)
        return response.read()