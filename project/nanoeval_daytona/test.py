import os
from pathlib import Path
from dotenv import load_dotenv
from daytona_sdk import Daytona, DaytonaConfig, CreateSandboxParams, LspLanguageId, SandboxResources

# Load environment variables from .env.local
env_path = Path('.env.local')
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

def run_test():
    # Configure Daytona client
    config = DaytonaConfig()
    daytona = Daytona(config)
    
    # Create sandbox parameters
    params = CreateSandboxParams(
        language=LspLanguageId.PYTHON,
        resources=SandboxResources(
            cpu=2,
            memory=4,
            disk=10
        ),
        autoStopInterval=30
    )
    
    try:
        # Create a sandbox (synchronous, not async)
        print("Creating Daytona sandbox...")
        sandbox = daytona.create(params)  # Not using await here
        print(f"Sandbox created with ID: {sandbox.id}")
        
        # Execute code in the sandbox
        print("Executing code in sandbox...")
        result = sandbox.process.code_run("print('Hello from Daytona sandbox!')")
        print(f"Execution result: {result}")
        
        # Clean up
        print("Cleaning up sandbox...")
        daytona.remove(sandbox)
        print("Sandbox removed")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()