import json
from datetime import timedelta
from io import BytesIO
from urllib.parse import quote
from miniopy_async import Minio

from table_service.app.core.settings import app_settings

DOWNLOAD_URL_TTL = timedelta(minutes=10)


class ExportStorage:
    XLSX_MEDIA_TYPE = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    def __init__(self, client: Minio, public: Minio, bucket_name: str) -> None:
        self._client = client
        self._public = public
        self._bucket_name = bucket_name

    async def ensure_file_bucket(self) -> None:
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

    async def upload_excel_file(
        self, object_name: str, content: BytesIO, length: int
    ) -> None:
        """Загружает аватар, возвращает object key (его и храним в БД)."""
        await self._client.put_object(
            bucket_name=app_settings.MINIO_EXPORT_BUCKET,
            object_name=object_name,
            data=content,
            length=length,
            content_type=self.XLSX_MEDIA_TYPE,
        )

    async def presigned_download_url(self, object_name: str, filename: str) -> str:
        """
        Returns:
        str: Подписанный URL для скачивания, действительный в течение DOWNLOAD_URL_TTL.
        Например:
        http://localhost:9000/exports/tables/1/abc123.xlsx?
        X-Amz-Algorithm=AWS4-HMAC-SHA256&
        X-Amz-Credential=minioadmin%2F20260101%2Fus-east-1%2Fs3%2Faws4_request&
        X-Amz-Date=20260101T120000Z&
        X-Amz-Expires=600&
        X-Amz-Signature=..
        """
        encoded = quote(filename)
        return await self._public.presigned_get_object(
            bucket_name=self._bucket_name,
            object_name=object_name,
            expires=DOWNLOAD_URL_TTL,
            response_headers={
                "response-content-disposition": f"attachment; filename*=UTF-8''{encoded}"
            },
        )


def _make_client(endpoint: str, server_url: str | None = None) -> Minio:
    return Minio(
        endpoint=endpoint,
        access_key=app_settings.MINIO_ACCESS_KEY,
        secret_key=app_settings.MINIO_SECRET_KEY,
        secure=app_settings.MINIO_SECURE,
        server_url=server_url,
    )


export_storage = ExportStorage(
    client=_make_client(app_settings.MINIO_ENDPOINT),
    public=_make_client(
        app_settings.MINIO_ENDPOINT,
        server_url=app_settings.MINIO_PUBLIC_URL,
    ),
    bucket_name=app_settings.MINIO_EXPORT_BUCKET,
)
