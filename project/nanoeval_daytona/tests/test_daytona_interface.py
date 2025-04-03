"""Tests for the Daytona sandbox integration."""

import os
import unittest.mock as mock

import pytest
from daytona_sdk import Daytona, DaytonaConfig, SandboxResources

from nanoeval_daytona.daytona_computer_interface import (
    DaytonaSandboxManager,
    DaytonaComputerInterface,
    DaytonaComputerRuntime,
)
from nanoeval_daytona.task_to_daytona_config import task_to_daytona_params
from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerConfiguration


@pytest.fixture
def mock_daytona():
    """Create a mock Daytona SDK instance."""
    with mock.patch("nanoeval_daytona.daytona_computer_interface.Daytona") as mock_daytona:
        # Mock sandbox instance
        mock_sandbox = mock.AsyncMock()
        mock_sandbox.id = "test-sandbox-id"
        mock_sandbox.process = mock.AsyncMock()
        mock_sandbox.shell = mock.AsyncMock()
        mock_sandbox.fs = mock.AsyncMock()
        
        # Mock Daytona instance
        mock_daytona_instance = mock_daytona.return_value
        mock_daytona_instance.create = mock.AsyncMock(return_value=mock_sandbox)
        mock_daytona_instance.remove = mock.AsyncMock()
        
        yield mock_daytona_instance, mock_sandbox


@pytest.mark.asyncio
async def test_sandbox_manager_creation(mock_daytona):
    """Test the creation of a Daytona sandbox manager."""
    mock_daytona_instance, _ = mock_daytona
    
    # Create sandbox manager
    manager = DaytonaSandboxManager()
    
    # Verify Daytona SDK was initialized correctly
    assert manager.daytona == mock_daytona_instance


@pytest.mark.asyncio
async def test_sandbox_creation(mock_daytona):
    """Test creating a Daytona sandbox."""
    mock_daytona_instance, mock_sandbox = mock_daytona
    
    # Create and use sandbox
    manager = DaytonaSandboxManager()
    sandbox = await manager.create_sandbox()
    
    # Verify correct parameters were passed
    mock_daytona_instance.create.assert_called_once()
    call_args = mock_daytona_instance.create.call_args[0][0]
    assert "language" in call_args
    assert "resources" in call_args
    assert call_args["resources"].cpu > 0
    
    # Verify sandbox was returned
    assert sandbox == mock_sandbox


@pytest.mark.asyncio
async def test_sandbox_code_execution(mock_daytona):
    """Test executing code in a Daytona sandbox."""
    _, mock_sandbox = mock_daytona
    
    # Mock successful code execution
    mock_sandbox.process.code_run.return_value = {
        "output": "Hello, World!\n",
        "result": "'Hello, World!'",
        "error": None,
    }
    
    # Create manager and execute code
    manager = DaytonaSandboxManager()
    result = await manager.execute_code(mock_sandbox, "print('Hello, World!')", 10)
    
    # Verify code was executed with correct parameters
    mock_sandbox.process.code_run.assert_called_once_with(
        "print('Hello, World!')", {"timeout": 10000}
    )
    
    # Verify result was returned correctly
    assert result["output"] == "Hello, World!\n"
    assert result["result"] == "'Hello, World!'"


@pytest.mark.asyncio
async def test_sandbox_file_operations(mock_daytona):
    """Test file operations in a Daytona sandbox."""
    _, mock_sandbox = mock_daytona
    
    # Mock file operations
    test_content = b"file content"
    mock_sandbox.fs.read_file.return_value = test_content
    
    # Create manager and perform file operations
    manager = DaytonaSandboxManager()
    await manager.upload_file(mock_sandbox, test_content, "/test/path.txt")
    content = await manager.download_file(mock_sandbox, "/test/path.txt")
    
    # Verify operations were called correctly
    mock_sandbox.fs.write_file.assert_called_once_with("/test/path.txt", test_content)
    mock_sandbox.fs.read_file.assert_called_once_with("/test/path.txt")
    
    # Verify content was returned correctly
    assert content == test_content


@pytest.mark.asyncio
async def test_task_to_daytona_params():
    """Test converting ComputerConfiguration to Daytona parameters."""
    # Create a test configuration
    config = ComputerConfiguration(
        docker_image="python:3.11",
        resources=mock.MagicMock(cpu=2, memory=4096),
        timeout=300,
        allow_internet=True,
    )
    
    # Convert to Daytona parameters
    params = task_to_daytona_params(config)
    
    # Verify parameters
    assert params["language"] == "python"
    assert isinstance(params["resources"], SandboxResources)
    assert params["resources"].cpu == 2
    assert params["resources"].memory == 4
    assert "autoStopInterval" in params
    assert params["autoStopInterval"] == 5  # 300 seconds = 5 minutes
    assert "pythonVersion" in params
    assert params["pythonVersion"] == "3.11"


@pytest.mark.asyncio
async def test_computer_interface(mock_daytona):
    """Test the DaytonaComputerInterface functionality."""
    _, mock_sandbox = mock_daytona
    
    # Mock successful code execution
    mock_sandbox.process.code_run.return_value = {
        "output": "Result: 42\n",
        "result": "42",
        "error": None,
    }
    
    # Mock shell command execution
    mock_sandbox.shell.exec.return_value = {
        "output": "Hello from shell\n",
        "exitCode": 0,
    }
    
    # Create manager and interface
    manager = DaytonaSandboxManager()
    interface = DaytonaComputerInterface(manager, mock_sandbox)
    
    # Test Python code execution
    result = await interface.execute("print('Result:', 21 + 21)")
    assert result.status == "success"
    assert result.output == "Result: 42\n"
    assert result.final_expression_output == "42"
    
    # Test shell command execution
    result = await interface.send_shell_command("echo 'Hello from shell'")
    assert result.exit_code == 0
    assert result.output.decode() == "Hello from shell\n"
    
    # Test file operations
    test_content = b"test file content"
    await interface.upload(test_content, "/test/file.txt")
    content = await interface.download("/test/file.txt")
    assert content == test_content
    
    # Test container name retrieval (sandbox ID)
    container_names = await interface.fetch_container_names()
    assert container_names == ["test-sandbox-id"]
    
    # Test stopping the sandbox
    await interface.stop()
    mock_sandbox.manager.remove.assert_called_once()
