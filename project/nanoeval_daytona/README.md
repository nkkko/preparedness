# Nanoeval Daytona Integration

This package provides integration between nanoeval and Daytona sandboxes for code execution in isolated environments.

## Features

- Execute evaluation code in secure, isolated Daytona sandboxes
- Configurable resource limits and environment settings
- Compatible with the existing nanoeval evaluation framework
- Support for Python code execution and shell commands

## Configuration

Configure the integration using environment variables. Copy `.env.example` to `.env.local` and edit the values:

```bash
# Copy the example configuration
cp .env.example .env.local

# Edit the configuration with your values
nano .env.local
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DAYTONA_API_KEY` | Authentication key for Daytona API | (required) |
| `DAYTONA_SERVER_URL` | URL of the Daytona API server | (required) |
| `DAYTONA_TARGET` | Target location for sandbox creation | (required) |
| `DAYTONA_SANDBOX_CPU` | CPU cores allocated to sandboxes | 2 |
| `DAYTONA_SANDBOX_MEMORY` | Memory in GB allocated to sandboxes | 4 |
| `DAYTONA_SANDBOX_DISK` | Disk space in GB allocated to sandboxes | 10 |
| `DAYTONA_AUTO_STOP_INTERVAL` | Minutes until auto-stop | 30 |
| `DAYTONA_TIMEOUT` | Default timeout for code execution in seconds | 180 |

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