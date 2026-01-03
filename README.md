# Little Snitch Rule Manager

[![Lint](https://github.com/mlevin2/little-snitch-rule-manager/actions/workflows/lint.yml/badge.svg)](https://github.com/mlevin2/little-snitch-rule-manager/actions/workflows/lint.yml)

A CLI tool for managing Little Snitch rules on macOS, specifically optimized for handling binaries that change frequently (like those installed via Homebrew) by automating binary hash updates.

## Features

- **Automated Rule Management**: Add or update Little Snitch rules via the command line.
- **Hash Management**: Automatically calculates SHA256 hashes of binaries and updates Little Snitch `codeRequirements`.
- **Enforced `fileHash` Type**: Automatically converts `trustedAnchor` requirements to `fileHash` to support binaries without stable team identifiers. This is particularly useful for fixing issues where Little Snitch rejects rules for Homebrew-installed binaries (like `mosh-server`) because their `authorIdentifier` is just a hash instead of a valid Apple Team ID.
- **Safety First**: Automatically exports a backup of your Little Snitch configuration to `~/.ls_backups/` before making any modifications.
- **Symlink Support**: Correctly resolves symlinks (common with Homebrew) to ensure the actual binary is hashed.

## How it Works

1. **Backup**: The tool exports the current Little Snitch model to a JSON file.
2. **Hash**: It calculates the SHA256 hash of the target binary.
3. **Find Requirement**: it searches the `codeRequirements` in the config for an existing entry matching the binary.
4. **Patch**:
    - It updates the hash in the requirement.
    - If the requirement type is not `fileHash`, it converts it and removes any `authorIdentifier`.
5. **Rule Update**: It adds or replaces a rule for the specified binary, ports, and protocol.
6. **Restore**: It tells Little Snitch to restore the model from the modified JSON.

## Prerequisites

- **macOS** with **Little Snitch** (tested with Little Snitch 6).
- **Python 3.13+** (managed via `uv`).
- **uv**: A fast Python package installer and resolver.

## Setup

The project uses `uv` for dependency management and `pre-commit` for quality assurance.

```bash
# Sync dependencies and create virtual environment
uv sync

# Install git hooks
uv run pre-commit install
```

## Usage

The main functionality is currently provided by `ls_manage.py`.

### Allow a Binary

To allow a binary through the firewall with specific ports and protocol:

```bash
uv run ls_manage.py allow /usr/local/bin/mosh-server --ports "60000-61000" --protocol udp
```

#### Arguments:
- `path`: Path to the binary (e.g., `/usr/local/bin/mosh-server`).
- `--ports`: Port or port range (e.g., `80`, `60000-61000`).
- `--protocol`: `udp` or `tcp` (default: `udp`).
- `--direction`: `incoming`, `outgoing`, or `both` (default: `both`).
- `--remote`: Remote scope like `any` or `local-net` (default: `any`).
- `--replace`: If specified, removes existing rules for this binary before adding the new one.

### Backups & Undo

Every time you run a command that modifies your configuration, a backup is saved to `~/.ls_backups/ls_backup_<timestamp>.json`.

To revert a change, you can use the command provided in the output of the script:
```bash
sudo "/Applications/Little Snitch.app/Contents/Components/littlesnitch" -u $USER restore-model ~/.ls_backups/ls_backup_<timestamp>.json
```

## Development

### Standards
This project follows **Spec-Driven Development (SDD)** and strict linting standards. Refer to the `.specify/memory/constitution.md` for core principles.

### Linting
The project uses `ruff` for linting and formatting. You can run it manually:
```bash
uv run ruff check .        # Linting check
uv run ruff format .       # Auto-format code
uv run ruff check . --fix  # Fix auto-fixable issues
```

### Testing
Run tests using pytest:
```bash
uv run pytest              # Run all tests
uv run pytest -v           # Run with verbose output
uv run pytest --cov        # Run with coverage report
uv run pytest tests/test_ls_manage.py  # Run specific test file
```

Test files are located in the `tests/` directory. Tests cover:
- Binary hash calculation and symlink resolution
- Code requirement lookup for Homebrew packages
- Configuration file backup and restore
- Rule creation and updates
- Command execution and error handling

### Git Hooks & CI/CD
Pre-commit hooks are enforced locally. If you run `uv run pre-commit install`, the hooks will automatically:
1. Run `ruff` to fix any auto-fixable linting issues.
2. Run `ruff-format` to ensure consistent code styling.
3. Block the commit if non-fixable issues remain.

The GitHub Actions CI pipeline (`.github/workflows/lint.yml`) runs on all push and pull requests to `main` and performs:
- Linting checks with `ruff check`
- Format verification with `ruff format --check`

### Branching & Merging
- **Branches**: MUST use the `NNN-short-description` format.
- **Merging**: MUST use `--no-ff` when merging to `main`.
