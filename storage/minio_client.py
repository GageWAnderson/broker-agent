import base64
import io
import logging
import uuid
from typing import BinaryIO
from urllib.parse import urlparse

import httpx
from minio import Minio
from minio.error import S3Error

from broker_agent.config import settings
from broker_agent.config.settings import config

logger = logging.getLogger(__name__)


class MinioConnector:
    """Handles connection and basic operations with a Minio S3-compatible storage."""

    def __init__(self) -> None:
        """Initializes the Minio client using configuration settings."""
        self.client: Minio | None = None
        try:
            self.client = Minio(
                settings.config.MINIO_ENDPOINT,
                access_key=settings.config.MINIO_ROOT_USER,
                secret_key=settings.config.MINIO_ROOT_PASSWORD,
                secure=False,  # Set to True if using HTTPS
            )
            # Verify connection by listing buckets
            self.client.list_buckets()
            logger.info(
                f"Successfully connected to Minio at {settings.config.MINIO_ENDPOINT}"
            )
        except S3Error as e:
            logger.error(f"Error connecting to Minio: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"An unexpected error occurred during Minio connection: {e}")
            self.client = None

    def is_connected(self) -> bool:
        """Checks if the client is successfully connected to Minio."""
        return self.client is not None

    def list_buckets(self) -> list[str]:
        """Lists all buckets in the Minio instance.

        Returns:
            list[str]: A list of bucket names.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot list buckets.")
            return []
        try:
            buckets = self.client.list_buckets()  # type: ignore
            return [bucket.name for bucket in buckets]
        except S3Error as e:
            logger.error(f"Error listing buckets: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred listing buckets: {e}")
            return []

    def make_bucket(self, bucket_name: str) -> bool:
        """Creates a new bucket if it doesn't already exist.

        Args:
            bucket_name (str): The name of the bucket to create.

        Returns:
            bool: True if the bucket was created or already exists, False otherwise.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot create bucket.")
            return False
        try:
            if not self.client.bucket_exists(bucket_name):  # type: ignore
                self.client.make_bucket(bucket_name)  # type: ignore
                logger.info(f"Bucket '{bucket_name}' created successfully.")
            return True
        except S3Error as e:
            logger.error(f"Error creating bucket '{bucket_name}': {e}")
            return False
        except Exception as e:
            logger.error(
                f"An unexpected error occurred creating bucket '{bucket_name}': {e}"
            )
            return False

    def upload_file(self, bucket_name: str, object_name: str, file_path: str) -> bool:
        """Uploads a file to the specified bucket.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The object name in the bucket.
            file_path (str): The file path to upload.

        Returns:
            bool: True if the file was uploaded successfully, False otherwise.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot upload file.")
            return False
        try:
            # Create bucket if it doesn't exist
            if not self.make_bucket(bucket_name):
                return False

            self.client.fput_object(bucket_name, object_name, file_path)  # type: ignore
            return True
        except S3Error as e:
            logger.error(f"Error uploading file to '{bucket_name}/{object_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred uploading file: {e}")
            return False

    def upload_data(
        self, bucket_name: str, object_name: str, data: BinaryIO, length: int
    ) -> bool:
        """Uploads data from a file-like object to the specified bucket.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The object name in the bucket.
            data (BinaryIO): The binary data to upload.
            length (int): The length of the data in bytes.

        Returns:
            bool: True if the data was uploaded successfully, False otherwise.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot upload data.")
            return False
        try:
            # Create bucket if it doesn't exist
            if not self.make_bucket(bucket_name):
                return False

            self.client.put_object(bucket_name, object_name, data, length)  # type: ignore
            return True
        except S3Error as e:
            logger.error(f"Error uploading data to '{bucket_name}/{object_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred uploading data: {e}")
            return False

    def download_file(self, bucket_name: str, object_name: str, file_path: str) -> bool:
        """Downloads a file from the specified bucket.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The object name in the bucket.
            file_path (str): The file path to save the downloaded object.

        Returns:
            bool: True if the file was downloaded successfully, False otherwise.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot download file.")
            return False
        try:
            self.client.fget_object(bucket_name, object_name, file_path)  # type: ignore
            return True
        except S3Error as e:
            logger.error(
                f"Error downloading file from '{bucket_name}/{object_name}': {e}"
            )
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred downloading file: {e}")
            return False

    def list_objects(self, bucket_name: str, prefix: str = "") -> list[str]:
        """Lists objects in the specified bucket with an optional prefix.

        Args:
            bucket_name (str): The name of the bucket.
            prefix (str, optional): Prefix of the objects to list. Defaults to "".

        Returns:
            list[str]: A list of object names.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot list objects.")
            return []
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)  # type: ignore
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing objects in bucket '{bucket_name}': {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred listing objects: {e}")
            return []

    def remove_object(self, bucket_name: str, object_name: str) -> bool:
        """Removes an object from the specified bucket.

        Args:
            bucket_name (str): The name of the bucket.
            object_name (str): The object name to remove.

        Returns:
            bool: True if the object was removed successfully, False otherwise.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot remove object.")
            return False
        try:
            self.client.remove_object(bucket_name, object_name)  # type: ignore
            logger.info(f"Object '{bucket_name}/{object_name}' removed successfully.")
            return True
        except S3Error as e:
            logger.error(f"Error removing object '{bucket_name}/{object_name}': {e}")
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred removing object: {e}")
            return False

    async def download_image(self, img_url: str) -> str | None:
        """Downloads an image from a URL, uploads it to Minio, and returns the Minio URL.

        This method fetches an image from the provided URL, determines its content type,
        generates a unique filename, and uploads it to the configured Minio bucket.

        Args:
            img_url (str): The URL of the image to download.

        Returns:
            Optional[str]: The URL of the uploaded image in Minio if successful, None otherwise.
        """
        if not self.is_connected():
            logger.error("Minio connector is not available.")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    img_url, follow_redirects=True, timeout=30.0
                )
                response.raise_for_status()  # Raise exception for 4xx/5xx status codes

            image_content = response.content
            content_type = response.headers.get(
                "content-type", "image/webp"
            )  # Default to webp
            extension = content_type.split("/")[-1] if "/" in content_type else "webp"
            object_name = f"{uuid.uuid4()}.{extension}"

            # Ensure bucket exists (make_bucket handles existing)
            if not self.make_bucket(config.minio_bucket):
                logger.error(
                    f"Failed to ensure Minio bucket '{config.minio_bucket}' exists."
                )
                return None

            success = self.upload_data(
                bucket_name=config.minio_bucket,
                object_name=object_name,
                data=io.BytesIO(image_content),
                length=len(image_content),
            )

            if success:
                minio_url = f"{config.minio_bucket}/{object_name}"
                logger.debug(f"Successfully uploaded {img_url} to {minio_url}")
                return minio_url
            else:
                logger.error(
                    f"Failed to upload image {img_url} to Minio bucket {config.minio_bucket}."
                )
                return None

        except httpx.RequestError as e:
            logger.error(f"HTTP error downloading image {img_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing image {img_url}: {e}")
            return None

    async def get_object_as_base64(
        self, url: str
    ) -> tuple[str | None, str | None]:
        """
        Retrieve an object from Minio and return it as base64 encoded data along with its mime type.

        This method accepts both "bucket/object" style paths and full URLs (e.g., "http://host:port/bucket/object").
        It robustly extracts the bucket and object name from the input, retrieves the object data,
        determines the content type (MIME type), and encodes the data as a base64 string.

        Minio stores user metadata keys in lowercase, but Content-Type may also appear as a header,
        so both "content-type" and "Content-Type" are checked when determining the MIME type.

        Args:
            url (str): The Minio URL in format "bucket_name/object_name" or a full URL.

        Returns:
            Tuple[Optional[str], Optional[str]]: A tuple containing (base64_encoded_data, mime_type),
            or (None, None) if unsuccessful.
        """
        if not self.is_connected():
            logger.warning("Not connected to Minio. Cannot get object.")
            return None, None

        try:
            if url.startswith("http://") or url.startswith("https://"):
                parsed = urlparse(url)
                path = parsed.path.lstrip("/")
                parts = path.split("/", 1)
            else:
                parts = url.split("/", 1)

            if len(parts) != 2 or not parts[0] or not parts[1]:
                logger.error(
                    f"Invalid Minio URL format: {url}. Expected 'bucket/object' or full URL."
                )
                return None, None

            bucket_name, object_name = parts

            response = self.client.get_object(bucket_name, object_name)  # type: ignore
            data = response.read()

            stat = self.client.stat_object(bucket_name, object_name)  # type: ignore
            mime_type = (
                stat.metadata.get("content-type")
                or stat.metadata.get("Content-Type")
                or "application/octet-stream"
            )

            base64_data = base64.b64encode(data).decode("utf-8")

            return base64_data, mime_type

        except S3Error as e:
            logger.error(f"Error retrieving object '{url}' from Minio: {e}")
            return None, None
        except Exception as e:
            logger.error(f"An unexpected error occurred retrieving object: {e}")
            return None, None


connector = MinioConnector()
