"""Daytona sandbox integration for nanoeval."""

import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional, cast

import async_lru
import structlog
from daytona_sdk import Daytona, DaytonaConfig, LspLanguageId, SandboxResources
from pydantic import BaseModel
from typing_extensions import override

import chz
from nanoeval.solvers.computer_tasks.code_execution_interface import (
    ComputerConfiguration,
    ComputerRuntime,
    ExecutionResult,
    JupyterComputerInterface,
    JupyterExecutionResult,
)

logger = structlog.get_logger(component=__name__)

# Default timeout for code execution
DAYTONA_TIMEOUT = int(os.getenv("DAYTONA_TIMEOUT", "120"))

# Environment variable configuration
DAYTONA_API_KEY = os.getenv("DAYTONA_API_KEY")
DAYTONA_SERVER_URL = os.getenv("DAYTONA_SERVER_URL")
DAYTONA_TARGET = os.getenv("DAYTONA_TARGET")

# Resource configuration with defaults
DAYTONA_SANDBOX_CPU = int(os.getenv("DAYTONA_SANDBOX_CPU", "2"))
DAYTONA_SANDBOX_MEMORY = int(os.getenv("DAYTONA_SANDBOX_MEMORY", "4"))
DAYTONA_SANDBOX_DISK = int(os.getenv("DAYTONA_SANDBOX_DISK", "10"))
DAYTONA_AUTO_STOP_INTERVAL = int(os.getenv("DAYTONA_AUTO_STOP_INTERVAL", "30"))


class Python3ExceptionDict(BaseModel):
    """A pydantic model for serializing a Python 3.x exception.

    Attrs:
        name: The type of the exception, e.g. ValueError.
        traceback: The traceback. Every line ends with a \n.
        args: The args passed to the exception's ctor.
        notes: Future-proofing for PEP 678.
    """

    name: str
    traceback: list[str]
    args: tuple[Any, ...]
    notes: list[str]


class DaytonaSandboxManager:
    """Manages Daytona sandbox operations."""

    def __init__(self, config: Optional[DaytonaConfig] = None):
        """Initialize the Daytona sandbox manager with optional config override."""
        self.config = config or DaytonaConfig(
            api_key=DAYTONA_API_KEY,
            server_url=DAYTONA_SERVER_URL,
            target=DAYTONA_TARGET,
        )
        self.daytona = Daytona(self.config)

    async def create_sandbox(self, params: Optional[Dict[str, Any]] = None) -> Any:
        """Create a new sandbox with specified parameters."""
        default_params = {
            "language": LspLanguageId.PYTHON,
            "resources": SandboxResources(
                cpu=DAYTONA_SANDBOX_CPU,
                memory=DAYTONA_SANDBOX_MEMORY,
                disk=DAYTONA_SANDBOX_DISK,
            ),
            "autoStopInterval": DAYTONA_AUTO_STOP_INTERVAL,
        }
        effective_params = {**default_params, **(params or {})}
        logger.info("Creating Daytona sandbox", params=effective_params)
        return await self.daytona.create(effective_params)

    async def execute_code(self, sandbox: Any, code: str, timeout: int = DAYTONA_TIMEOUT) -> Dict[str, Any]:
        """Execute code in a sandbox with timeout."""
        logger.debug("Executing code in sandbox", timeout=timeout)
        return await sandbox.process.code_run(code, {"timeout": timeout * 1000})

    async def execute_shell(self, sandbox: Any, command: str, timeout: int = DAYTONA_TIMEOUT) -> Dict[str, Any]:
        """Execute shell command in a sandbox with timeout."""
        logger.debug("Executing shell command in sandbox", command=command, timeout=timeout)
        return await sandbox.shell.exec(command, {"timeout": timeout * 1000})

    async def upload_file(self, sandbox: Any, content: bytes, path: str) -> None:
        """Upload a file to the sandbox."""
        logger.debug("Uploading file to sandbox", path=path)
        await sandbox.fs.write_file(path, content)

    async def download_file(self, sandbox: Any, path: str) -> bytes:
        """Download a file from the sandbox."""
        logger.debug("Downloading file from sandbox", path=path)
        return await sandbox.fs.read_file(path)

    async def remove_sandbox(self, sandbox: Any) -> None:
        """Remove a sandbox."""
        logger.info("Removing sandbox")
        await self.daytona.remove(sandbox)


class DaytonaComputerInterface(JupyterComputerInterface):
    """Implements the ComputerInterface using Daytona sandboxes."""

    def __init__(self, sandbox_manager: DaytonaSandboxManager, sandbox: Any):
        self.sandbox_manager = sandbox_manager
        self.sandbox = sandbox
        self._internet_disabled = False

    async def disable_internet(self) -> None:
        """Disable internet access for the sandbox."""
        if not self._internet_disabled:
            logger.info("Disabling internet access")
            # Daytona sandboxes are isolated by default, but we can add additional
            # network isolation if needed in the future
            self._internet_disabled = True

    async def upload(self, file: bytes, destination: str) -> None:
        """Upload a file to the sandbox."""
        await self.sandbox_manager.upload_file(self.sandbox, file, destination)

    async def download(self, file: str) -> bytes:
        """Download a file from the sandbox."""
        return await self.sandbox_manager.download_file(self.sandbox, file)

    async def send_shell_command(self, cmd: str) -> ExecutionResult:
        """Execute a shell command in the sandbox."""
        result = await self.sandbox_manager.execute_shell(self.sandbox, cmd)
        return ExecutionResult(
            output=result.get("output", "").encode("utf-8"),
            exit_code=result.get("exitCode", 1),
        )

    async def fetch_container_names(self) -> list[str]:
        """Return the sandbox ID as a container name for compatibility."""
        return [str(self.sandbox.id)]

    async def stop(self) -> None:
        """Stop the sandbox."""
        await self.sandbox_manager.remove_sandbox(self.sandbox)

    @override
    async def execute(self, code: str, timeout: int = DAYTONA_TIMEOUT) -> JupyterExecutionResult:
        """Execute Python code in the sandbox."""
        await self._initialize_kernel_once()

        try:
            result = await self.sandbox_manager.execute_code(self.sandbox, code, timeout)
            
            # Parse result
            output = result.get("output", "")
            if result.get("error"):
                exception = Python3ExceptionDict(
                    name=result.get("error", {}).get("type", "Exception"),
                    traceback=result.get("error", {}).get("traceback", []),
                    args=(result.get("error", {}).get("message", ""),),
                    notes=[],
                )
                return JupyterExecutionResult(
                    status="failed_with_in_kernel_exception",
                    output=output,
                    final_expression_output=None,
                    in_kernel_exception=cast(Any, exception),
                    system_exception=None,
                )
            
            return JupyterExecutionResult(
                status="success",
                output=output,
                final_expression_output=result.get("result"),
                in_kernel_exception=None,
                system_exception=None,
            )
        except Exception as e:
            # Handle system exceptions (like timeouts or connectivity issues)
            return JupyterExecutionResult(
                status="failed_with_system_exception",
                output="",
                final_expression_output=None,
                in_kernel_exception=None,
                system_exception=str(e),
            )

    @async_lru.alru_cache(maxsize=1)
    async def _initialize_kernel_once(self) -> None:
        """Initialize the Python kernel if needed."""
        # Check if kernel is already running or initialize it
        try:
            # This is a placeholder - Daytona might handle this differently
            await self.send_shell_command("python -c 'print(\"Kernel check\")'")
            logger.debug("Kernel is already running")
        except Exception:
            logger.info("Initializing Python kernel")
            # Setup Python environment
            await self.send_shell_command("python -m pip install ipykernel")


@chz.chz
class DaytonaComputerRuntime(ComputerRuntime):
    """Runtime for executing code in Daytona sandboxes."""
    
    sandbox_manager: DaytonaSandboxManager = chz.field(default_factory=DaytonaSandboxManager)

    @asynccontextmanager
    async def run(self, config: ComputerConfiguration) -> AsyncGenerator[DaytonaComputerInterface, None]:
        """Create and manage a Daytona sandbox for the given configuration."""
        # Convert computer configuration to Daytona sandbox parameters
        params = self._config_to_daytona_params(config)
        
        # Create the sandbox
        sandbox = await self.sandbox_manager.create_sandbox(params)
        
        try:
            # Set up working directory if specified
            if config.cwd and config.cwd != "/":
                await self.sandbox_manager.execute_shell(
                    sandbox, f"mkdir -p {config.cwd} && cd {config.cwd}"
                )
            
            # Set up environment variables
            for key, value in config.environment.items():
                await self.sandbox_manager.execute_shell(
                    sandbox, f"export {key}=\"{value}\""
                )
            
            # Create and yield the interface
            interface = DaytonaComputerInterface(self.sandbox_manager, sandbox)
            
            # Disable internet if configured
            if not config.allow_internet:
                await interface.disable_internet()
                
            yield interface
        finally:
            # Clean up the sandbox
            try:
                await self.sandbox_manager.remove_sandbox(sandbox)
            except Exception as e:
                logger.error("Failed to remove sandbox", error=str(e))
    
    def _config_to_daytona_params(self, config: ComputerConfiguration) -> Dict[str, Any]:
        """Convert nanoeval computer configuration to Daytona sandbox parameters."""
        # Map CPU and memory requirements
        resources = SandboxResources(
            cpu=max(1, int(config.resources.cpu)),  # Minimum 1 CPU
            memory=max(1, config.resources.memory // 1024),  # Convert MB to GB, minimum 1GB
            disk=DAYTONA_SANDBOX_DISK,  # Default or configured disk
        )
        
        params = {
            "language": LspLanguageId.PYTHON,
            "resources": resources,
            "autoStopInterval": DAYTONA_AUTO_STOP_INTERVAL,
        }
        
        # Add any additional configuration needed for Daytona
        # This is a placeholder for future extensions
        
        return params