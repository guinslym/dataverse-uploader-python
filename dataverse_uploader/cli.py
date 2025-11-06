"""Command-line interface for the Dataverse uploader."""

import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from dotenv import load_dotenv

from dataverse_uploader.core.config import UploaderConfig
from dataverse_uploader.core.exceptions import UploaderException
from dataverse_uploader.uploaders.dataverse import DataverseUploader

# Load .env file explicitly
load_dotenv()

# Create a simple app instance without subcommands
console = Console()


def main(
    paths: List[Path] = typer.Argument(
        ...,
        help="Files or directories to upload",
        exists=True,
    ),
    server: Optional[str] = typer.Option(
        None,
        "--server",
        "-s",
        help="Dataverse server URL (e.g., https://dataverse.example.org)",
        envvar="DV_SERVER_URL",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--key",
        "-k",
        help="API key for authentication",
        envvar="DV_API_KEY",
    ),
    dataset: Optional[str] = typer.Option(
        None,
        "--dataset",
        "--did",
        "-d",
        help="Dataset persistent identifier (DOI)",
        envvar="DV_DATASET_PID",
    ),
    list_only: bool = typer.Option(
        False,
        "--list-only",
        "-l",
        help="List files without uploading",
    ),
    verify: bool = typer.Option(
        False,
        "--verify",
        "-v",
        help="Verify checksums before and after upload",
    ),
    recurse: bool = typer.Option(
        False,
        "--recurse",
        "-r",
        help="Recursively process subdirectories",
    ),
    force_new: bool = typer.Option(
        False,
        "--force-new",
        help="Upload even if files already exist",
    ),
    skip: int = typer.Option(
        0,
        "--skip",
        help="Number of files to skip",
        min=0,
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of files to upload",
        min=1,
    ),
    traditional_upload: bool = typer.Option(
        False,
        "--traditional",
        help="Use traditional upload instead of direct upload",
    ),
    fixity_algorithm: str = typer.Option(
        "MD5",
        "--fixity",
        help="Hash algorithm for checksums (MD5, SHA-1, SHA-256)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log",
        help="Path to log file",
    ),
):
    """Upload files or directories to a Dataverse dataset.
    
    Examples:
    
        # Upload a single file
        dv-upload file.csv -s https://demo.dataverse.org -k API_KEY -d doi:10.xxxx/yyyy
        
        # Upload a directory recursively
        dv-upload data/ -s https://demo.dataverse.org -k API_KEY -d doi:10.xxxx/yyyy --recurse
        
        # List files without uploading
        dv-upload data/ -s https://demo.dataverse.org -k API_KEY -d doi:10.xxxx/yyyy --list-only
    """
    try:
        # Create configuration
        config = UploaderConfig(
            server_url=server,
            api_key=api_key,
            dataset_pid=dataset,
            list_only=list_only,
            verify_checksums=verify,
            recurse_directories=recurse,
            force_new=force_new,
            skip_files=skip,
            max_files=limit,
            direct_upload=not traditional_upload,
            fixity_algorithm=fixity_algorithm,
            verbose=verbose,
            log_file=log_file,
        )
        
        # Create uploader
        with DataverseUploader(config) as uploader:
            console.print(f"[bold blue]Dataverse Uploader v1.3.0[/bold blue]")
            console.print(f"Server: {server}")
            console.print(f"Dataset: {dataset}")
            console.print()
            
            if list_only:
                console.print("[yellow]LIST ONLY MODE - No files will be uploaded[/yellow]")
            
            # Process uploads
            uploader.process_requests([str(p) for p in paths])
            
            console.print()
            console.print("[bold green]✓ Upload complete![/bold green]")
            console.print(f"Files uploaded: {uploader.uploaded_files}")
            console.print(f"Files skipped: {uploader.skipped_files}")
            console.print(f"Bytes uploaded: {uploader.uploaded_bytes:,}")
            
    except UploaderException as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Upload interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


# Create the Typer app with the main function as the default command
app = typer.Typer(add_completion=False)
app.command()(main)


if __name__ == "__main__":
    app()