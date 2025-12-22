"""
Development environment setup script.
Creates a virtual environment and installs dependencies.
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    """Set up the development environment."""
    project_root = Path(__file__).parent
    venv_path = project_root / ".venv"
    requirements_file = project_root / "requirements.txt"
    
    print("🔧 Setting up development environment...")
    
    # Create virtual environment if it doesn't exist
    if not venv_path.exists():
        print(f"📦 Creating virtual environment at {venv_path}...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True
            )
            print("✅ Virtual environment created successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return 1
    else:
        print(f"✅ Virtual environment already exists at {venv_path}")
    
    # Determine the python executable in the virtual environment
    if os.name == "nt":  # Windows
        python_executable = venv_path / "Scripts" / "python.exe"
        pip_executable = venv_path / "Scripts" / "pip.exe"
        activate_script = venv_path / "Scripts" / "Activate.ps1"
    else:  # Unix-like
        python_executable = venv_path / "bin" / "python"
        pip_executable = venv_path / "bin" / "pip"
        activate_script = venv_path / "bin" / "activate"
    
    # Upgrade pip
    print("📦 Upgrading pip...")
    try:
        subprocess.run(
            [str(python_executable), "-m", "pip", "install", "--upgrade", "pip"],
            check=True
        )
        print("✅ pip upgraded successfully!")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Failed to upgrade pip: {e}")
    
    # Install requirements if requirements.txt exists
    if requirements_file.exists():
        print(f"📦 Installing dependencies from {requirements_file}...")
        try:
            subprocess.run(
                [str(pip_executable), "install", "-r", str(requirements_file)],
                check=True
            )
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return 1
    else:
        print(f"⚠️  No requirements.txt found at {requirements_file}")
    
    # Install package in editable mode if setup.py exists
    setup_file = project_root / "setup.py"
    if setup_file.exists():
        print("📦 Installing package in editable mode...")
        try:
            subprocess.run(
                [str(pip_executable), "install", "-e", "."],
                cwd=str(project_root),
                check=True
            )
            print("✅ Package installed in editable mode!")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Failed to install package: {e}")
    
    # Print activation instructions
    print("\n" + "="*60)
    print("✅ Development environment setup complete!")
    print("="*60)
    print("\n🚀 To activate the virtual environment, run:")
    if os.name == "nt":
        print(f"   {activate_script}")
        print("   or")
        print(f"   .venv\\Scripts\\Activate.ps1")
    else:
        print(f"   source {activate_script}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
