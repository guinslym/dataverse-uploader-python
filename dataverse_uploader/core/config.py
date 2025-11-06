"""Configuration management for the uploader."""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class UploaderConfig(BaseSettings):
    """Configuration for the Dataverse uploader.
    
    Settings can be loaded from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_prefix="DV_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields instead of raising error
        populate_by_name=True,  # Allow both field name and alias
    )

    # Server configuration
    server_url: str = Field(
        ...,
        description="Dataverse server URL (e.g., https://dataverse.example.org)"
    )
    api_key: Optional[str] = Field(
        None,
        description="API key for authentication"
    )
    
    # Dataset configuration
    dataset_pid: Optional[str] = Field(
        None,
        description="Dataset persistent identifier (DOI)"
    )
    dataverse_alias: Optional[str] = Field(
        None,
        description="Dataverse collection alias"
    )
    
    # Upload settings
    verify_checksums: bool = Field(
        False,
        description="Verify file checksums before and after upload"
    )
    direct_upload: bool = Field(
        True,
        description="Use direct upload to S3 (if enabled on server)"
    )
    single_file_mode: bool = Field(
        False,
        description="Upload each file separately instead of batching"
    )
    recurse_directories: bool = Field(
        False,
        description="Recursively process subdirectories"
    )
    
    # Limits and retries
    max_files: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum number of files to upload (None for unlimited)"
    )
    skip_files: int = Field(
        0,
        ge=0,
        description="Number of files to skip before starting upload"
    )
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for failed uploads"
    )
    timeout_seconds: int = Field(
        1200,
        gt=0,
        description="HTTP request timeout in seconds"
    )
    max_wait_lock_seconds: int = Field(
        60,
        gt=0,
        description="Maximum time to wait for dataset lock to release"
    )
    
    # Performance settings
    http_concurrency: int = Field(
        4,
        gt=0,
        le=20,
        description="Number of concurrent HTTP connections"
    )
    multipart_chunk_size: int = Field(
        5 * 1024 * 1024,  # 5 MB
        gt=0,
        description="Chunk size for multipart uploads (bytes)"
    )
    
    # File handling
    fixity_algorithm: str = Field(
        "MD5",
        description="Hash algorithm for file integrity (MD5, SHA-1, SHA-256)"
    )
    fix_invalid_names: bool = Field(
        True,
        description="Replace invalid characters in filenames with underscores"
    )
    no_ingest: bool = Field(
        False,
        description="Skip Dataverse tabular file ingestion"
    )
    
    # Behavior flags
    list_only: bool = Field(
        False,
        description="List files that would be uploaded without actually uploading"
    )
    force_new: bool = Field(
        False,
        description="Create new entries even if files already exist"
    )
    trust_all_certs: bool = Field(
        False,
        description="Trust all SSL certificates (USE WITH CAUTION)"
    )
    
    # Logging
    log_file: Optional[Path] = Field(
        None,
        description="Path to log file (None for stdout only)"
    )
    verbose: bool = Field(
        False,
        description="Enable verbose logging"
    )

    @field_validator("fixity_algorithm")
    @classmethod
    def validate_algorithm(cls, v: str) -> str:
        """Validate hash algorithm."""
        valid = {"MD5", "SHA-1", "SHA-256", "SHA-512"}
        v_upper = v.upper()
        if v_upper not in valid:
            raise ValueError(f"Algorithm must be one of {valid}")
        return v_upper

    @field_validator("server_url")
    @classmethod
    def validate_server_url(cls, v: str) -> str:
        """Ensure server URL doesn't have trailing slash."""
        return v.rstrip("/")

    def get_hash_algorithm_name(self) -> str:
        """Get the hash algorithm name in Python's hashlib format."""
        mapping = {
            "MD5": "md5",
            "SHA-1": "sha1",
            "SHA-256": "sha256",
            "SHA-512": "sha512",
        }
        return mapping[self.fixity_algorithm]