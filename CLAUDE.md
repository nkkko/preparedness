# Development Guide for Claude

## Build & Test Commands
- Install: `pip install -e .`
- Run all tests: `pytest`
- Run specific test: `pytest project/nanoeval/nanoeval/path/to/test.py::test_name`
- Run with parallel workers: `pytest -xvs -n auto`
- Lint code: `ruff check .`
- Format code: `ruff format .` and `black .`

## Code Style Guidelines
- **Python Version**: 3.11+
- **Line Length**: 100 characters max
- **Typing**: Use type annotations throughout; `from typing import Any, List, Dict` etc.
- **Imports**: Sorted with `ruff` - standard libs first, then third-party, then project imports
- **Error Handling**: Use appropriate exception types; document exceptions in docstrings
- **Naming**: 
  - Classes: `PascalCase`
  - Functions/methods: `snake_case`
  - Variables: `snake_case`
- **Asyncio**: Prefer async/await patterns for I/O operations
- **Testing**: All functionality should have corresponding pytest tests
- **Comments**: Document "why" not "what"; avoid unnecessary comments

## Project Structure
The codebase consists of multiple sub-projects (nanoeval, alcatraz, paperbench, etc.) with independent functionality but shared conventions.

## Daytona Sandbox Integration
This project is being updated to support running evaluations in Daytona sandboxes:
- Use `daytona_sdk` for sandbox management and execution
- Configure via environment variables: `DAYTONA_API_KEY`, `DAYTONA_SERVER_URL`, `DAYTONA_TARGET`
- Sandboxes provide isolated environments for running code execution tasks
- Implementation focuses on Python language support via `LspLanguageId.PYTHON`
- Resource allocation configurable via `SandboxResources` (CPU, memory, disk)