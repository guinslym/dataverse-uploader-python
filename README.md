# Dataverse Uploader (Python)

A Python implementation of the DVUploader command-line bulk uploader for Dataverse repositories. This tool provides efficient bulk file uploads with features like checksum verification, resume capability, and direct S3 uploads.

[![YouTube Tutorial](https://img.shields.io/badge/YouTube-Tutorial-red?style=for-the-badge&logo=youtube)](https://youtu.be/dEPccXpUs9w)

**📺 Watch the Tutorial**: [Dataverse Uploader Python - Complete Guide](https://youtu.be/dEPccXpUs9w)

## Features

- **Bulk uploads**: Upload hundreds or thousands of files efficiently
- **Direct upload**: Direct-to-S3 uploads when enabled on the server
- **Checksum verification**: MD5, SHA-1, SHA-256, SHA-512 support
- **Resume capability**: Skip already uploaded files automatically
- **Recursive directory processing**: Upload entire directory trees
- **Connection pooling**: Efficient HTTP connection management
- **Retry logic**: Automatic retry with exponential backoff
- **Progress tracking**: Real-time upload statistics
- **Flexible configuration**: Environment variables, CLI arguments, or config files

## Architecture

### Package Structure

```
dataverse_uploader/
├── __init__.py
├── cli.py                       # Command-line interface
│
├── core/
│   ├── __init__.py
│   ├── abstract_uploader.py    # Base uploader with core logic
│   ├── config.py                # Configuration management (Pydantic)
│   └── exceptions.py            # Custom exception hierarchy
│
├── resources/
│   ├── __init__.py
│   ├── base.py                  # Abstract Resource interface
│   └── file_resource.py         # Local file/directory handling
│
├── uploaders/
│   ├── __init__.py
│   └── dataverse.py             # Dataverse-specific implementation
│
└── utils/
    ├── __init__.py
    └── http_client.py           # HTTP session with pooling & retries
```

### Design Patterns

**Abstract Factory Pattern**: `Resource` abstraction allows uniform handling of local files, remote files, and BagIt bags.

**Strategy Pattern**: `AbstractUploader` defines the upload algorithm; specific implementations (`DataverseUploader`) provide repository-specific strategies.

**Template Method Pattern**: `AbstractUploader.process_requests()` defines the workflow; subclasses implement specific steps like `upload_file()` and `create_directory()`.

**Configuration as Code**: Pydantic models for type-safe configuration with validation.

## Installation

### Prerequisites

- Python 3.9 or higher
- pip or poetry

### From Source

```bash
git clone https://github.com/your-org/dataverse-uploader-python.git
cd dataverse-uploader-python
pip install -e .
```

### Using Poetry

```bash
poetry install
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Configuration

### Environment Variables (.env file)

Create a `.env` file in the project root:

```env
DV_SERVER_URL=https://demo.dataverse.org
DV_API_KEY=your-api-key-here
DV_DATASET_PID=doi:10.5072/FK2/ABCDEF
DV_VERIFY_CHECKSUMS=true
DV_RECURSE_DIRECTORIES=true
```

### Configuration Options

| Option | CLI Flag | Environment Variable | Default | Description |
|--------|----------|---------------------|---------|-------------|
| Server URL | `--server` / `-s` | `DV_SERVER_URL` | - | Dataverse server URL |
| API Key | `--key` / `-k` | `DV_API_KEY` | - | Authentication API key |
| Dataset PID | `--dataset` / `-d` | `DV_DATASET_PID` | - | Dataset DOI |
| Verify Checksums | `--verify` / `-v` | `DV_VERIFY_CHECKSUMS` | `false` | Verify file integrity |
| Recurse | `--recurse` / `-r` | `DV_RECURSE_DIRECTORIES` | `false` | Process subdirectories |
| Direct Upload | `--traditional` | `DV_DIRECT_UPLOAD` | `true` | Use S3 direct upload |
| Skip Files | `--skip N` | `DV_SKIP_FILES` | `0` | Number of files to skip |
| Max Files | `--limit N` | `DV_MAX_FILES` | `None` | Maximum files to upload |
| List Only | `--list-only` / `-l` | `DV_LIST_ONLY` | `false` | Preview without uploading |
| Force New | `--force-new` | `DV_FORCE_NEW` | `false` | Upload even if exists |
| Fixity Algorithm | `--fixity` | `DV_FIXITY_ALGORITHM` | `MD5` | Hash algorithm |
| Verbose | `--verbose` | `DV_VERBOSE` | `false` | Enable verbose logging |
| Timeout | - | `DV_TIMEOUT_SECONDS` | `1200` | Request timeout (seconds) |
| HTTP Concurrency | - | `DV_HTTP_CONCURRENCY` | `4` | Concurrent connections |

## Usage

### Command Line

#### Basic Upload

```bash
dv-upload my_data.csv \
  --server https://demo.dataverse.org \
  --key YOUR_API_KEY \
  --dataset doi:10.5072/FK2/ABCDEF
```

#### Upload Directory Recursively

```bash
dv-upload research_data/ \
  --server https://demo.dataverse.org \
  --key YOUR_API_KEY \
  --dataset doi:10.5072/FK2/ABCDEF \
  --recurse
```

#### With Checksum Verification

```bash
dv-upload data/ \
  -s https://demo.dataverse.org \
  -k YOUR_API_KEY \
  -d doi:10.5072/FK2/ABCDEF \
  --verify \
  --recurse
```

#### Preview Upload (List Only Mode)

```bash
dv-upload data/ \
  -s https://demo.dataverse.org \
  -k YOUR_API_KEY \
  -d doi:10.5072/FK2/ABCDEF \
  --list-only \
  --recurse
```
#### Creating dummy files to upload on Dataverse
```bash
python examples\generate_large_files.py # choose option 1
#or
python examples\create_csv_files.py  
#then
dv-upload data/ --recurse --verify
#or
dv-upload *.csv --recurse --verify
```


#### Using Environment Variables

With a `.env` file configured:

```bash
dv-upload data/ --recurse --verify
```

#### Multiple Files

```bash
dv-upload file1.csv file2.xlsx data_folder/ --recurse
```

### Python API

```python
from pathlib import Path
from dataverse_uploader.core.config import UploaderConfig
from dataverse_uploader.uploaders.dataverse import DataverseUploader

# Configure uploader
config = UploaderConfig(
    server_url="https://demo.dataverse.org",
    api_key="your-api-key",
    dataset_pid="doi:10.5072/FK2/ABCDEF",
    verify_checksums=True,
    recurse_directories=True,
)

# Upload files
with DataverseUploader(config) as uploader:
    uploader.process_requests(["data/file1.csv", "data/dir1/"])
    
    print(f"Uploaded: {uploader.uploaded_files} files")
    print(f"Skipped: {uploader.skipped_files} files")
    print(f"Failed: {uploader.failed_files} files")
    print(f"Total bytes: {uploader.uploaded_bytes:,}")
```

## Common Use Cases

### Upload CSV Files

Dataverse automatically converts CSV files to `.tab` format:

```bash
# Upload CSV
dv-upload customers.csv --verify

# Dataverse stores as: customers.tab
# Re-upload detects existing file even with different extension
dv-upload customers.csv --verify  # Skips (already exists as .tab)
```

### Upload Directory Structure

```bash
# Upload preserving directory structure
dv-upload project_data/ --recurse

# Structure in Dataverse:
# project_data/
# ├── raw/data.csv
# ├── processed/results.csv
# └── docs/README.md
```

### Resume After Interruption

```bash
# Start upload
dv-upload large_dataset/ --recurse --verify
# Press Ctrl+C to interrupt

# Resume - skips already uploaded files
dv-upload large_dataset/ --recurse --verify
```

### Upload with Retry

The uploader automatically retries failed uploads:

```bash
dv-upload data/ --recurse --verify

# Output:
# Files uploaded: 3
# Files failed: 2
# 
# Retry attempt 1/3 for 2 failed files...
# Successfully uploaded on retry: file1.csv
# Successfully uploaded on retry: file2.csv
# 
# Final: All files uploaded successfully!
```

## Testing

### Generate Test Files

Use the included test file generator:

```bash
cd examples
python generate_large_files.py

# Select option:
# 0 - Quick demo (15 MB, ~10 seconds)
# 1 - Small files (30 MB, ~30 seconds)
# 2 - Medium files (250 MB, ~3-5 minutes)
# 3 - Large files (1 GB, ~10-15 minutes)
```

See [GENERATE_LARGE_FILES.md](docs/GENERATE_LARGE_FILES.md) for full documentation.

### Run Tests

```bash
# Preview what will be uploaded
dv-upload data/ --list-only --recurse

# Upload files
dv-upload data/ --recurse --verify

# Verify duplicate detection (should skip all)
dv-upload data/ --recurse --verify
```

## Troubleshooting

### Connection Errors

```bash
# Trust all certificates (testing only!)
export DV_TRUST_ALL_CERTS=true
dv-upload data/ --recurse
```

### Large Files Timeout

```bash
# Increase timeout to 1 hour
export DV_TIMEOUT_SECONDS=3600
dv-upload large_file.zip --verify
```

### Dataset Locked

The uploader automatically waits for locks to clear:

```bash
# Adjust max wait time (default: 60 seconds)
export DV_MAX_WAIT_LOCK_SECONDS=300
dv-upload data/ --recurse
```

### View Detailed Logs

```bash
# Enable verbose logging
dv-upload data/ --recurse --verbose

# Save logs to file
export DV_LOG_FILE=upload.log
dv-upload data/ --recurse --verbose
```

### Duplicate Files

The uploader detects duplicates by:
1. **Exact filename match** (e.g., `file.csv`)
2. **Converted format** (e.g., `file.csv` → `file.tab`)
3. **Content hash** (with `--verify` flag)

```bash
# Upload CSV
dv-upload data.csv --verify

# Try uploading again
dv-upload data.csv --verify
# Output: File exists as data.tab (tabular file converted to TAB)
#         Files skipped: 1
```

## Advanced Features

### Direct Upload to S3

When enabled on the server, files are uploaded directly to S3:

```bash
# Direct upload (default)
dv-upload large_file.bin --verify

# Traditional upload through Dataverse API
dv-upload large_file.bin --verify --traditional
```

### Checksum Verification

Verify file integrity before and after upload:

```bash
# Calculate and verify MD5 checksums
dv-upload data/ --verify --recurse

# Use different algorithm
export DV_FIXITY_ALGORITHM=SHA-256
dv-upload data/ --verify --recurse
```

### Batch Upload Limits

Control batch size and limits:

```bash
# Skip first 10 files
dv-upload data/ --skip 10 --recurse

# Upload maximum 100 files
dv-upload data/ --limit 100 --recurse

# Combine both
dv-upload data/ --skip 10 --limit 50 --recurse
```

## Project Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical architecture and design patterns
- **[PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)** - Project overview and implementation status
- **[GENERATE_LARGE_FILES.md](docs/GENERATE_LARGE_FILES.md)** - Test file generation guide
- **[.env.example](.env.example)** - Configuration template

## Examples

See the [examples/](examples/) directory for:

- `simple_upload.py` - Basic programmatic upload
- `create_csv_files.py` - Generate sample CSV files
- `generate_large_files.py` - Generate test files of various sizes

## Development

### Setup Development Environment

```bash
git clone https://github.com/your-org/dataverse-uploader-python.git
cd dataverse-uploader-python
poetry install
```

### Run Tests

```bash
pytest
pytest --cov=dataverse_uploader --cov-report=html
```

### Code Quality

```bash
# Format code
black dataverse_uploader tests examples

# Lint
ruff check dataverse_uploader tests examples

# Type check
mypy dataverse_uploader
```

### Project Structure

```
dataverse_uploader_python/
├── .env.example                 # Configuration template
├── .gitignore                   # Git ignore rules
├── pyproject.toml               # Project metadata & dependencies
├── requirements.txt             # Direct dependencies
├── README.md                    # This file
│
├── dataverse_uploader/          # Main package
│   ├── __init__.py
│   ├── cli.py                   # CLI entry point
│   ├── core/                    # Core components
│   ├── resources/               # Resource abstraction
│   ├── uploaders/               # Repository implementations
│   └── utils/                   # Utilities
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── PROJECT_SUMMARY.md
│   └── GENERATE_LARGE_FILES.md
│
├── examples/                    # Usage examples
│   ├── simple_upload.py
│   ├── create_csv_files.py
│   └── generate_large_files.py
│
└── tests/                       # Test suite (to be implemented)
    └── ...
```

## Extending the Uploader

### Adding a New Repository Type

Create a new uploader class:

```python
from dataverse_uploader.core.abstract_uploader import AbstractUploader

class MyRepoUploader(AbstractUploader):
    def validate_configuration(self) -> None:
        # Validate config
        pass
    
    def upload_file(self, file, parent_path) -> Optional[str]:
        # Upload implementation
        pass
    
    # Implement other abstract methods...
```

### Adding New Resource Types

Extend the `Resource` base class:

```python
from dataverse_uploader.resources.base import Resource

class URLResource(Resource):
    def __init__(self, url: str):
        self.url = url
    
    def get_input_stream(self):
        # Stream from URL
        pass
    
    # Implement other methods...
```

## Comparison: Java vs Python

### Core Concepts Preserved

| Java | Python | Notes |
|------|--------|-------|
| `AbstractUploader` | `AbstractUploader` | Template method pattern |
| `Resource` interface | `Resource` ABC | Abstract base class |
| `FileResource` | `FileResource` | Concrete implementation |
| `DVUploader` | `DataverseUploader` | Dataverse-specific logic |
| Apache HttpClient | `httpx` | Modern async-capable client |
| Maven `pom.xml` | `pyproject.toml` | Build configuration |
| Properties files | Pydantic Settings | Type-safe configuration |

### Python Advantages

1. **Type Safety**: Pydantic models provide runtime validation
2. **Async Ready**: Built on httpx for future async support
3. **Better Error Handling**: Rich exception hierarchy
4. **Modern Tooling**: Black, Ruff, MyPy for code quality
5. **Rich CLI**: Beautiful terminal output with progress bars
6. **Simpler Deployment**: No JVM required

## Performance Considerations

### Connection Pooling

- Maintains pool of HTTP connections
- Reuses connections for multiple uploads
- Configurable pool size (default: 4)

### Memory Management

- Streams large files (doesn't load entirely in memory)
- Chunked reading for hash calculation
- Batch processing for CSV/JSON generation

### Retry Logic

- Automatic retry with exponential backoff
- Network errors: 3 attempts with 2s, 4s, 8s delays
- Failed uploads: 3 retry attempts with 5s, 10s, 20s delays

## Video Tutorial

📺 **Watch the complete tutorial**: [Dataverse Uploader Python - Complete Guide](https://youtu.be/dEPccXpUs9w)

The tutorial covers:
- Installation and setup
- Basic usage and commands
- Environment configuration
- Uploading files and directories
- Checksum verification
- Troubleshooting common issues
- Advanced features

## License

Apache License 2.0

## Credits

Python implementation inspired by the original Java DVUploader developed by:
- Texas Digital Library
- Global Dataverse Community Consortium
- University of Michigan
- NCSA/SEAD Project

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code passes quality checks
5. Submit a pull request

## Support

- **Issues**: https://github.com/your-org/dataverse-uploader-python/issues
- **Wiki**: https://github.com/your-org/dataverse-uploader-python/wiki
- **Tutorial**: https://youtu.be/dEPccXpUs9w
- **Dataverse Community**: https://dataverse.org

## Quick Reference

```bash
# Basic upload
dv-upload file.csv -s SERVER -k API_KEY -d DOI

# Directory upload
dv-upload data/ --recurse --verify

# Preview only
dv-upload data/ --list-only --recurse

# With environment variables
export DV_SERVER_URL=https://demo.dataverse.org
export DV_API_KEY=your-key
export DV_DATASET_PID=doi:10.xxxx/yyyy
dv-upload data/ --recurse

# Generate test files
cd examples
python generate_large_files.py  # Select 0 for quick demo

# Upload test files
cd ..
dv-upload data/ --recurse --verify
```

## FAQ

**Q: Why are my CSV files showing as .tab in Dataverse?**  
A: Dataverse automatically converts tabular files (CSV, Excel, SPSS, Stata, SAS, R data) to `.tab` format during ingestion. The uploader detects this and won't create duplicates.

**Q: How do I upload large files (>1GB)?**  
A: Use direct upload (default) and increase timeout: `export DV_TIMEOUT_SECONDS=3600`

**Q: Can I resume after interruption?**  
A: Yes! Just run the same command again. The uploader skips already-uploaded files.

**Q: How do I verify files weren't corrupted during upload?**  
A: Use the `--verify` flag to calculate and verify checksums.

**Q: What if uploads keep failing?**  
A: The uploader automatically retries failed uploads up to 3 times. Check logs with `--verbose` for details.

**Q: Can I use this in CI/CD pipelines?**  
A: Yes! See the [GENERATE_LARGE_FILES.md](docs/GENERATE_LARGE_FILES.md) for CI/CD integration examples.

---

**Ready to get started?** Check out the [video tutorial](https://youtu.be/dEPccXpUs9w) or dive into the [Quick Start](#quick-start) guide above! 🚀