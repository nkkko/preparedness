# Daytona Sandbox Integration Specification

## Overview
This specification outlines the integration of Daytona sandboxes into the evaluation framework to provide secure, isolated environments for executing code during evaluations. The integration will leverage Daytona's SDK to create, manage, and interact with sandboxes that run evaluation tasks.

## Goals
- Provide isolated execution environments for evaluations
- Ensure consistent, reproducible evaluation environments
- Enable resource control and monitoring for evaluation workloads
- Simplify deployment across different environments

## Architecture

### Components
1. **Daytona Interface Layer**
   - Wraps the Daytona SDK for sandbox operations
   - Provides a consistent API for sandbox interactions
   - Handles configuration and authentication

2. **Evaluation Executor**
   - Manages the lifecycle of evaluation sandboxes
   - Maps evaluation tasks to sandbox execution
   - Collects results from sandbox executions

3. **Resource Controller**
   - Defines and applies resource constraints
   - Monitors resource usage during evaluations
   - Implements timeouts and termination policies

### Integration Points
- `nanoeval/solvers/computer_tasks/code_execution_interface.py`: Primary interface for code execution
- `project/nanoeval_alcatraz/nanoeval_alcatraz/alcatraz_computer_interface.py`: Adaptation layer
- `project/nanoeval/nanoeval/evaluation.py`: Evaluation workflow integration

## Implementation Details

### Daytona SDK Integration
```python
from daytona_sdk import Daytona, DaytonaConfig, LspLanguageId, SandboxResources

class DaytonaSandboxManager:
    def __init__(self, config=None):
        """Initialize the Daytona sandbox manager with optional config override."""
        self.config = config or DaytonaConfig()
        self.daytona = Daytona(self.config)
        
    async def create_sandbox(self, params=None):
        """Create a new sandbox with specified parameters."""
        default_params = {
            'language': 'python',
            'resources': SandboxResources(
                cpu=2,
                memory=4,
                disk=10
            ),
            'autoStopInterval': 30  # auto-stop after 30 minutes of inactivity
        }
        params = {**default_params, **(params or {})}
        return await self.daytona.create(params)
        
    async def execute_code(self, sandbox, code, timeout=60):
        """Execute code in a sandbox with timeout."""
        return await sandbox.process.code_run(code, {'timeout': timeout * 1000})
```

### Execution Interface Adapter
```python
from nanoeval.solvers.computer_tasks.code_execution_interface import CodeExecutionInterface

class DaytonaExecutionInterface(CodeExecutionInterface):
    """Adapter that implements CodeExecutionInterface using Daytona sandboxes."""
    
    def __init__(self, sandbox_manager):
        self.sandbox_manager = sandbox_manager
        self.current_sandbox = None
        
    async def initialize(self):
        """Initialize and prepare the sandbox for execution."""
        self.current_sandbox = await self.sandbox_manager.create_sandbox()
        
    async def execute_code(self, code, timeout=60):
        """Execute code in the sandbox."""
        if not self.current_sandbox:
            await self.initialize()
        return await self.sandbox_manager.execute_code(self.current_sandbox, code, timeout)
        
    async def cleanup(self):
        """Clean up resources when done with execution."""
        if self.current_sandbox:
            await self.sandbox_manager.daytona.remove(self.current_sandbox)
            self.current_sandbox = None
```

## Configuration
The integration will use environment variables for configuration:

- `DAYTONA_API_KEY`: Authentication key for Daytona services
- `DAYTONA_SERVER_URL`: URL of the Daytona API server
- `DAYTONA_TARGET`: Target location for sandbox creation

Additional configuration options:
- `DAYTONA_SANDBOX_CPU`: CPU cores (default: 2)
- `DAYTONA_SANDBOX_MEMORY`: Memory in GB (default: 4)
- `DAYTONA_SANDBOX_DISK`: Disk space in GB (default: 10)
- `DAYTONA_AUTO_STOP_INTERVAL`: Minutes until auto-stop (default: 30)

## Security Considerations
- All code execution occurs in isolated sandboxes
- Sandboxes have no access to local system resources
- Resource limits prevent denial-of-service attacks
- Timeouts ensure evaluations don't run indefinitely
- Credentials are managed via environment variables, not code

## Testing Strategy
1. **Unit Tests**:
   - Test the Daytona interface layer with mocked SDK
   - Verify configuration handling and error cases

2. **Integration Tests**:
   - Create actual sandboxes in a test environment
   - Run simple evaluation tasks and verify results
   - Test resource limits and timeout behaviors

3. **Performance Tests**:
   - Measure sandbox creation time
   - Evaluate parallel execution capabilities
   - Compare execution performance to current methods

## Implementation Plan
1. Add Daytona SDK as a dependency
2. Implement the Daytona interface layer
3. Create adapter for the code execution interface
4. Update evaluation workflows to use sandboxes
5. Add configuration options and documentation
6. Implement comprehensive tests
7. Performance optimization and tuning

## Requirements
- Python 3.11+
- Access to Daytona API
- Appropriate API credentials
- Network access from evaluation environment to Daytona services