import json
import uuid
from io import BytesIO

from miniopy_async import Minio

from auth_service.app.config import auth_service_settings as settings

minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)

_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def ensure_avatar_bucket() -> None:
    """Создаёт бакет и делает его read-only публичным (для прямых ссылок)."""
    bucket = settings.MINIO_BUCKET
    if not await minio_client.bucket_exists(bucket):
        await minio_client.make_bucket(bucket_name=bucket)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }
        ],
    }
    await minio_client.set_bucket_policy(bucket, json.dumps(policy))


async def upload_avatar(content: bytes, content_type: str) -> str:
    """Загружает аватар, возвращает object key (его и храним в БД)."""
    object_name = f"avatars/{uuid.uuid4().hex}{_EXTENSIONS[content_type]}"
    await minio_client.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name


async def delete_avatar(object_name: str | None) -> None:
    """Удалить аватар"""
    if not object_name:
        return
    await minio_client.remove_object(settings.MINIO_BUCKET, object_name)


def avatar_public_url(object_name: str | None) -> str | None:
    if not object_name:
        return None
    return f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{object_name}"
