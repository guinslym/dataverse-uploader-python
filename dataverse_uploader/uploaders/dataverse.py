"""Dataverse-specific uploader implementation."""

import logging
import time
from typing import Optional

import orjson

from dataverse_uploader.core.abstract_uploader import AbstractUploader
from dataverse_uploader.core.config import UploaderConfig
from dataverse_uploader.core.exceptions import (
    DatasetLockedError,
    NetworkError,
    UploaderException,
    UploadError,
)
from dataverse_uploader.resources.base import Resource

logger = logging.getLogger(__name__)


class DataverseUploader(AbstractUploader):
    """Uploader implementation for Dataverse repositories."""

    def __init__(self, config: UploaderConfig):
        """Initialize Dataverse uploader.
        
        Args:
            config: Configuration object
        """
        super().__init__(config)
        self.dataset_metadata: Optional[dict] = None
        self.existing_files: dict[str, dict] = {}

    def validate_configuration(self) -> None:
        """Validate Dataverse-specific configuration.
        
        Raises:
            UploaderException: If configuration is invalid
        """
        if not self.config.server_url:
            raise UploaderException("Server URL is required")
        
        if not self.config.api_key:
            raise UploaderException("API key is required")
        
        if not self.config.dataset_pid:
            raise UploaderException("Dataset persistent identifier (DOI) is required")
        
        # Verify dataset exists and is accessible
        self._load_dataset_metadata()

    def _load_dataset_metadata(self) -> None:
        """Load metadata for the target dataset."""
        logger.info(f"Loading dataset metadata for {self.config.dataset_pid}")
        
        url = (
            f"{self.config.server_url}/api/datasets/:persistentId/"
            f"?persistentId={self.config.dataset_pid}"
        )
        
        try:
            response = self.http_client.get(url)
            data = orjson.loads(response.content)
            
            if data.get("status") != "OK":
                raise UploaderException(f"Failed to load dataset: {data}")
            
            self.dataset_metadata = data.get("data", {})
            logger.info(f"Dataset loaded: {self.dataset_metadata.get('id')}")
            
            # Load existing files
            self._load_existing_files()
            
        except Exception as e:
            raise UploaderException(f"Failed to load dataset metadata: {e}")

    def _load_existing_files(self) -> None:
        """Load list of files already in the dataset."""
        logger.info("Loading existing files from dataset")
        
        url = (
            f"{self.config.server_url}/api/datasets/:persistentId/versions/:latest/files"
            f"?persistentId={self.config.dataset_pid}"
        )
        
        try:
            response = self.http_client.get(url)
            data = orjson.loads(response.content)
            
            if data.get("status") != "OK":
                logger.warning("Could not load existing files")
                return
            
            files = data.get("data", [])
            
            # Build map of path -> file info
            for file_info in files:
                file_path = file_info.get("directoryLabel", "")
                if file_path:
                    file_path = f"{file_path}/{file_info.get('label', '')}"
                else:
                    file_path = file_info.get("label", "")
                
                checksum_info = file_info.get("dataFile", {}).get("checksum", {})
                
                self.existing_files[file_path] = {
                    "id": file_info.get("dataFile", {}).get("id"),
                    "checksum_type": checksum_info.get("type", "MD5"),
                    "checksum_value": checksum_info.get("value", ""),
                }
            
            logger.info(f"Found {len(self.existing_files)} existing files")
            
        except Exception as e:
            logger.warning(f"Failed to load existing files: {e}")

    def get_existing_resource_id(
        self, resource: Resource, parent_path: str
    ) -> Optional[str]:
        """Check if resource exists in Dataverse.
        
        Args:
            resource: Resource to check
            parent_path: Parent directory path
            
        Returns:
            File ID if exists, None otherwise
        """
        if resource.is_directory():
            # Dataverse doesn't have explicit directory entries
            return None
        
        # Build the file path as Dataverse would see it
        file_path = f"{parent_path.strip('/')}/{resource.get_name()}".lstrip("/")
        
        return self.existing_files.get(file_path, {}).get("id")

    def create_directory(self, directory: Resource, parent_path: str) -> str:
        """Dataverse doesn't explicitly create directories.
        
        Directories are created implicitly when files are uploaded.
        
        Args:
            directory: Directory resource
            parent_path: Parent path
            
        Returns:
            Virtual directory ID (just the path)
        """
        # Return the path as a virtual ID
        return f"{parent_path.rstrip('/')}/{directory.get_name()}"

    def upload_file(self, file: Resource, parent_path: str) -> Optional[str]:
        """Upload a file to Dataverse.
        
        Args:
            file: File resource to upload
            parent_path: Parent directory path
            
        Returns:
            File ID if successful, None otherwise
        """
        if self.config.direct_upload:
            return self._upload_file_direct(file, parent_path)
        else:
            return self._upload_file_traditional(file, parent_path)

    def _upload_file_traditional(
        self, file: Resource, parent_path: str
    ) -> Optional[str]:
        """Upload file using traditional Dataverse API.
        
        Args:
            file: File resource
            parent_path: Parent directory path
            
        Returns:
            File ID if successful
        """
        url = (
            f"{self.config.server_url}/api/datasets/:persistentId/add"
            f"?persistentId={self.config.dataset_pid}"
        )
        
        # Prepare directory label
        directory_label = parent_path.strip("/")
        
        # Prepare JSON metadata
        json_data = {
            "description": file.get_metadata().description if file.get_metadata() else "",
            "directoryLabel": directory_label if directory_label else None,
            "categories": [],
            "restrict": False,
        }
        
        try:
            # Open file stream
            file_stream = file.get_input_stream()
            
            # Prepare multipart form
            files = {
                "file": (file.get_name(), file_stream, file.get_mimetype()),
                "jsonData": (None, orjson.dumps(json_data), "application/json"),
            }
            
            # Upload
            response = self.http_client.post(url, files=files)
            result = orjson.loads(response.content)
            
            if result.get("status") == "OK":
                file_id = result.get("data", {}).get("files", [{}])[0].get("dataFile", {}).get("id")
                return str(file_id) if file_id else None
            else:
                logger.error(f"Upload failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to upload {file.get_name()}: {e}")
            return None
        finally:
            file_stream.close()

    def _upload_file_direct(self, file: Resource, parent_path: str) -> Optional[str]:
        """Upload file using direct upload to S3.
        
        Args:
            file: File resource
            parent_path: Parent directory path
            
        Returns:
            File ID if successful
        """
        # Request upload URLs from Dataverse
        url = (
            f"{self.config.server_url}/api/datasets/:persistentId/uploadurls"
            f"?persistentId={self.config.dataset_pid}"
            f"&size={file.length()}"
        )
        
        try:
            response = self.http_client.get(url)
            upload_info = orjson.loads(response.content).get("data", {})
            
            if "url" not in upload_info:
                logger.warning("Direct upload not available, falling back to traditional")
                return self._upload_file_traditional(file, parent_path)
            
            # Upload file to S3
            storage_id = upload_info["storageIdentifier"]
            upload_url = upload_info["url"]
            
            file_stream = file.get_input_stream()
            
            # Upload to S3
            s3_response = self.http_client.upload_multipart(upload_url, file_stream)
            etag = s3_response.headers.get("ETag", "").strip('"')
            
            file_stream.close()
            
            # Register file with Dataverse
            return self._register_uploaded_file(
                file, parent_path, storage_id, file.length(), etag
            )
            
        except NetworkError as e:
            # If direct upload is not supported (404), fall back to traditional
            if "404" in str(e) or "Direct upload not supported" in str(e):
                logger.warning(f"Direct upload not supported, falling back to traditional upload")
                return self._upload_file_traditional(file, parent_path)
            else:
                logger.error(f"Direct upload failed for {file.get_name()}: {e}")
                return None
        except Exception as e:
            logger.error(f"Direct upload failed for {file.get_name()}: {e}")
            return None

    def _register_uploaded_file(
        self,
        file: Resource,
        parent_path: str,
        storage_id: str,
        file_size: int,
        etag: str,
    ) -> Optional[str]:
        """Register a directly-uploaded file with Dataverse.
        
        Args:
            file: File resource
            parent_path: Parent directory
            storage_id: S3 storage identifier
            file_size: Size in bytes
            etag: S3 ETag
            
        Returns:
            File ID if successful
        """
        url = (
            f"{self.config.server_url}/api/datasets/:persistentId/addFiles"
            f"?persistentId={self.config.dataset_pid}"
        )
        
        directory_label = parent_path.strip("/") or None
        
        file_data = {
            "description": "",
            "directoryLabel": directory_label,
            "categories": [],
            "restrict": False,
            "storageIdentifier": storage_id,
            "fileName": file.get_name(),
            "mimeType": file.get_mimetype(),
            "checksum": {
                "@type": self.config.fixity_algorithm,
                "@value": file.get_hash(self.config.get_hash_algorithm_name()),
            },
        }
        
        try:
            payload = {"files": [file_data]}
            response = self.http_client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            
            result = orjson.loads(response.content)
            
            if result.get("status") == "OK":
                file_id = result.get("data", {}).get("files", [{}])[0].get("dataFile", {}).get("id")
                return str(file_id) if file_id else None
            else:
                logger.error(f"File registration failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to register {file.get_name()}: {e}")
            return None

    def verify_checksum(self, file: Resource, file_id: str) -> bool:
        """Verify file checksum matches the one in Dataverse.
        
        Args:
            file: Local file resource
            file_id: Dataverse file ID
            
        Returns:
            True if checksums match
        """
        # Find file in existing files map
        for path, info in self.existing_files.items():
            if info.get("id") == file_id:
                remote_hash = info.get("checksum_value", "").lower()
                hash_algo = info.get("checksum_type", "MD5")
                
                # Calculate local hash
                local_hash = file.get_hash(hash_algo.lower()).lower()
                
                return local_hash == remote_hash
        
        logger.warning(f"Could not find file {file_id} for verification")
        return False

    def _wait_for_dataset_unlock(self, max_wait_seconds: int = 60) -> None:
        """Wait for dataset lock to be released.
        
        Args:
            max_wait_seconds: Maximum time to wait
            
        Raises:
            DatasetLockedError: If dataset remains locked
        """
        url = f"{self.config.server_url}/api/datasets/:persistentId/locks?persistentId={self.config.dataset_pid}"
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            response = self.http_client.get(url)
            data = orjson.loads(response.content)
            
            locks = data.get("data", [])
            if not locks:
                logger.info("Dataset unlocked")
                return
            
            logger.info(f"Dataset locked, waiting... ({len(locks)} locks)")
            time.sleep(5)
        
        raise DatasetLockedError(
            f"Dataset still locked after {max_wait_seconds} seconds"
        )