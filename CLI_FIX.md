# CLI Fix Instructions

## Problem

The CLI was requiring you to type `dv-upload upload data/` instead of just `dv-upload data/`.

## Solution

I've fixed the CLI to work the way you expect. Download the fixed file and replace your current one.

## Steps to Fix

### Option 1: Download and Replace

1. Download: [cli_fixed.py](computer:///mnt/user-data/outputs/cli_fixed.py)
2. Replace your current file:

```powershell
# Navigate to your project
cd C:\Users\PCUSER\Downloads\dataverse_uploader_python

# Backup the old file (optional)
Copy-Item dataverse_uploader\cli.py dataverse_uploader\cli.py.bak

# Replace with the fixed version
Copy-Item cli_fixed.py dataverse_uploader\cli.py

# Reinstall to pick up changes
poetry install
```

### Option 2: Manual Fix

Open `dataverse_uploader\cli.py` in your editor and make these changes:

1. **Line 18**: Change `def upload(` to `def main(`
2. **Line 165-167**: Replace the `app` setup with:
```python
# Create the Typer app with the main function as the default command
app = typer.Typer(add_completion=False)
app.command()(main)
```
3. **Remove** the `@app.command()` decorator (if present) and the `version()` function

Then reinstall:
```powershell
poetry install
```

## Testing

After fixing, these commands should now work:

```powershell
# Check help
dv-upload --help

# List files (using .env variables)
dv-upload data/ --list-only --recurse

# Upload files
dv-upload file.csv

# Upload directory
dv-upload data/ --recurse
```

## What Changed

**Before:**
- Typer app had multiple commands ("upload", "version")
- Required: `dv-upload upload data/`

**After:**
- Single default command
- Works naturally: `dv-upload data/`

## Verify It Works

```powershell
# Should show help without error
dv-upload --help

# Should show main upload options, not subcommands
# You should see "PATHS" as the first argument
```

The help output should look like:

```
Usage: dv-upload [OPTIONS] PATHS...

Upload files or directories to a Dataverse dataset.

Arguments:
  PATHS...  Files or directories to upload  [required]

Options:
  -s, --server TEXT          Dataverse server URL
  -k, --key TEXT            API key for authentication
  -d, --dataset TEXT        Dataset persistent identifier (DOI)
  -l, --list-only           List files without uploading
  -r, --recurse             Recursively process subdirectories
  --help                    Show this message and exit.
```

## Troubleshooting

**If you still see "No such command":**
```powershell
# Force reinstall
poetry install --no-cache

# Or use pip in the virtual environment
poetry run pip install -e . --force-reinstall --no-deps
```

**If changes don't take effect:**
```powershell
# Exit and restart your terminal
# Or reactivate the virtual environment
poetry shell
exit
poetry shell
```

## Your Command Should Work Now!

```powershell
dv-upload data/ --list-only --recurse
```

This will now work as expected! 🎉