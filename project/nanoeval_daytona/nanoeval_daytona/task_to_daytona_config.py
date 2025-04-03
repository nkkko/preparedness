"""Utilities for converting ComputerConfiguration to Daytona sandbox configuration."""

from typing import Any, Dict, Optional

from daytona_sdk import LspLanguageId, SandboxResources

from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerConfiguration


def task_to_daytona_params(task: ComputerConfiguration) -> Dict[str, Any]:
    """Convert a ComputerConfiguration to Daytona sandbox parameters.
    
    Args:
        task: The computer task configuration to convert
        
    Returns:
        A dictionary of parameters for Daytona sandbox creation
    """
    # Convert CPU and memory requirements
    cpu = max(1, int(task.resources.cpu))  # Ensure at least 1 CPU
    memory = max(1, task.resources.memory // 1024)  # Convert MB to GB, minimum 1GB
    
    # Optional disk size from environment or task configuration
    disk = 10  # Default 10GB
    if task.alcatraz_limits and "disk" in task.alcatraz_limits:
        disk = task.alcatraz_limits["disk"]
        
    resources = SandboxResources(
        cpu=cpu,
        memory=memory,
        disk=disk,
    )
    
    # Base configuration
    params = {
        "language": LspLanguageId.PYTHON,
        "resources": resources,
    }
    
    # Add timeout if specified
    if task.timeout:
        params["autoStopInterval"] = task.timeout // 60  # Convert seconds to minutes
    
    # Additional Daytona-specific configurations can be added here
    # For example, specific Python version requirements or additional tools
    if task.docker_image and "python" in task.docker_image:
        # Try to extract Python version from image name if it's a Python image
        # e.g., python:3.11 -> 3.11
        try:
            version = task.docker_image.split(":")[1]
            if version.startswith("3."):
                params["pythonVersion"] = version
        except (IndexError, ValueError):
            pass
            
    return params
