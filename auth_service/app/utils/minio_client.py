import json
import uuid
from io import BytesIO
from miniopy_async import Minio

from auth_service.app.config import auth_service_settings as settings
from auth_service.app.exceptions import UnsupportedContentTypeException


class AvatarStorage:
    _EXTENSIONS = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    def __init__(self, client: Minio, bucket_name: str, public_url: str):
        self._client = client
        self._bucket_name = bucket_name
        self._public_url = public_url

    async def ensure_avatar_bucket(self) -> None:
        """Создаёт бакет и делает его read-only публичным (для прямых ссылок)."""
        if not await self._client.bucket_exists(self._bucket_name):
            await self._client.make_bucket(bucket_name=self._bucket_name)

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self._bucket_name}/*"],
                }
            ],
        }
        await self._client.set_bucket_policy(self._bucket_name, json.dumps(policy))

    async def upload_avatar(self, content: bytes, content_type: str) -> str:
        """Загружает аватар, возвращает object key (его и храним в БД)."""
        extension = self._EXTENSIONS.get(content_type)
        if extension is None:
            raise UnsupportedContentTypeException(
                f"Неподдерживаемый формат файла: {content_type}"
            )
        object_name = f"avatars/{uuid.uuid4().hex}{extension}"
        await self._client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
        return object_name

    async def delete(self, object_name: str | None) -> None:
        """Удалить аватар"""
        if not object_name:
            return
        await self._client.remove_object(self._bucket_name, object_name)

    def public_url(self, object_name: str | None) -> str | None:
        if not object_name:
            return None
        return f"{self._public_url}/{self._bucket_name}/{object_name}"


avatar_storage = AvatarStorage(
    client=Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    ),
    bucket_name=settings.MINIO_BUCKET,
    public_url=settings.MINIO_PUBLIC_URL,
)
