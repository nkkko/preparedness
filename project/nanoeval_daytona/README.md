# Nanoeval Daytona Integration

This package provides integration between nanoeval and Daytona sandboxes for code execution in isolated environments.

## Features

- Execute evaluation code in secure, isolated Daytona sandboxes
- Configurable resource limits and environment settings
- Compatible with the existing nanoeval evaluation framework
- Support for Python code execution and shell commands

## Configuration

Configure the integration using environment variables:

```
DAYTONA_API_KEY=your_api_key
DAYTONA_SERVER_URL=https://your-daytona-server.com
DAYTONA_TARGET=us
```

## Usage

```python
from nanoeval_daytona import DaytonaComputerRuntime
from nanoeval.solvers.computer_tasks.code_execution_interface import ComputerConfiguration

# Create a configuration
config = ComputerConfiguration(
    cwd="/workspace",
    docker_image="python:3.11",
    resources=ContainerResources(cpu=2, memory=4096)
)

# Use the Daytona runtime
runtime = DaytonaComputerRuntime()
async with runtime.run(config) as computer:
    # Execute code
    result = await computer.execute("print('Hello from Daytona sandbox!')")
    print(result.output)
```