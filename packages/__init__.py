# Packages module

# Import backend-kit as backend_kit to handle hyphen in directory name
import sys
from pathlib import Path

# Add the backend-kit directory to sys.modules with underscore name
backend_kit_path = Path(__file__).parent / "backend-kit"
sys.path.insert(0, str(backend_kit_path))

try:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "packages.backend_kit", backend_kit_path / "__init__.py"
    )
    backend_kit_module = importlib.util.module_from_spec(spec)
    sys.modules["packages.backend_kit"] = backend_kit_module
    spec.loader.exec_module(backend_kit_module)
except Exception as e:
    print(f"Failed to load backend_kit module: {e}")
