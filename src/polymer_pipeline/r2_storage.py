"""Almacenamiento en Cloudflare R2 (compatible S3).

Gestiona la subida, descarga y eliminación de PDFs en un bucket R2.
Usa boto3 con el endpoint de Cloudflare R2.
"""

from __future__ import annotations

import logging
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from polymer_pipeline.settings import (
    get_r2_access_key,
    get_r2_bucket_name,
    get_r2_endpoint,
    get_r2_secret_key,
)

logger = logging.getLogger(__name__)

MANIFEST_KEY = "manifest.json"


class R2Storage:
    """Cliente de almacenamiento para Cloudflare R2."""

    def __init__(
        self,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket_name: str | None = None,
    ) -> None:
        self._endpoint = endpoint_url or get_r2_endpoint()
        self._access_key = access_key or get_r2_access_key()
        self._secret_key = secret_key or get_r2_secret_key()
        self._bucket = bucket_name or get_r2_bucket_name()

        if not self._endpoint:
            raise ValueError("R2_ENDPOINT no configurado en variables de entorno")
        if not self._access_key or not self._secret_key:
            raise ValueError("R2_ACCESS_KEY / R2_SECRET_KEY no configurados")

        self._client = boto3.client(
            "s3",
            endpoint_url=self._endpoint,
            aws_access_key_id=self._access_key,
            aws_secret_access_key=self._secret_key,
            config=Config(signature_version="s3v4"),
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    def file_exists(self, key: str) -> bool:
        """Verifica si un archivo ya existe en R2."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    def upload_file(self, local_path: Path, r2_key: str) -> bool:
        """Sube un archivo local a R2.

        Returns True si éxito, False si falla.
        """
        try:
            self._client.upload_file(
                str(local_path),
                self._bucket,
                r2_key,
                ExtraArgs={"ContentType": "application/pdf"},
            )
            logger.info("[R2] Subido: %s", r2_key)
            return True
        except ClientError as e:
            logger.error("[R2] Error subiendo %s: %s", r2_key, e)
            return False

    def delete_file(self, key: str) -> bool:
        """Elimina un archivo de R2."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info("[R2] Eliminado: %s", key)
            return True
        except ClientError as e:
            logger.error("[R2] Error eliminando %s: %s", key, e)
            return False

    def delete_all(self) -> int:
        """Elimina todos los archivos del bucket.

        Retorna el número de archivos eliminados.
        """
        deleted = 0
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket):
                objects = page.get("Contents", [])
                if not objects:
                    continue
                delete_params = {
                    "Bucket": self._bucket,
                    "Objects": [{"Key": obj["Key"]} for obj in objects],
                }
                self._client.delete_objects(**delete_params)
                deleted += len(objects)
                logger.info("[R2] Eliminados %d objetos en lote", len(objects))
        except ClientError as e:
            logger.error("[R2] Error eliminando todo: %s", e)
        return deleted

    def list_files(self, prefix: str = "") -> list[dict]:
        """Lista archivos en R2 con metadatos básicos.

        Retorna lista de dicts con {key, size, last_modified}.
        """
        files: list[dict] = []
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            kwargs = {"Bucket": self._bucket}
            if prefix:
                kwargs["Prefix"] = prefix
            for page in paginator.paginate(**kwargs):
                for obj in page.get("Contents", []):
                    files.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                    })
        except ClientError as e:
            logger.error("[R2] Error listando archivos: %s", e)
        return files

    def get_bucket_info(self) -> dict:
        """Retorna información del bucket: cantidad de archivos y tamaño total."""
        count = 0
        total_size = 0
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket):
                for obj in page.get("Contents", []):
                    count += 1
                    total_size += obj["Size"]
        except ClientError as e:
            logger.error("[R2] Error obteniendo info del bucket: %s", e)
        return {"count": count, "total_size_bytes": total_size}

    def upload_manifest(self, local_path: Path) -> bool:
        """Sube manifest.json desde disco local a R2."""
        if not local_path.exists():
            logger.warning("[R2] Manifest local no encontrado: %s", local_path)
            return False
        try:
            self._client.upload_file(
                str(local_path),
                self._bucket,
                MANIFEST_KEY,
                ExtraArgs={"ContentType": "application/json"},
            )
            logger.info("[R2] Manifest sincronizado")
            return True
        except ClientError as e:
            logger.error("[R2] Error subiendo manifest: %s", e)
            return False

    def download_manifest(self, local_path: Path) -> bool:
        """Descarga manifest.json desde R2 a disco local."""
        try:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            self._client.download_file(self._bucket, MANIFEST_KEY, str(local_path))
            logger.info("[R2] Manifest descargado a %s", local_path)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.info("[R2] No hay manifest en R2 aún")
            else:
                logger.error("[R2] Error descargando manifest: %s", e)
            return False


def get_r2_client() -> R2Storage | None:
    """Factory que retorna un R2Storage si las credenciales están configuradas.

    Retorna None si faltan variables de entorno, para que el pipeline
    pueda funcionar sin R2.
    """
    if not get_r2_endpoint() or not get_r2_access_key() or not get_r2_secret_key():
        return None
    try:
        return R2Storage()
    except Exception as e:
        logger.warning("[R2] No se pudo inicializar: %s", e)
        return None
