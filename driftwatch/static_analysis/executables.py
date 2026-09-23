import os
import shutil
import sys
from pathlib import Path


def resolve_executable(name: str) -> str:
    """Resolve a console-script executable (e.g. "semgrep", "bandit")
    installed in the same environment as the currently running Python.

    A venv's console scripts live next to its python executable
    (Scripts/ on Windows, bin/ on POSIX) regardless of whether the venv
    has been "activated" -- activation only changes PATH, and PATH isn't
    reliably set correctly for a subprocess (e.g. python invoked directly
    without activation, or a deployment environment with an unexpected
    PATH). Resolving via sys.executable's directory works either way."""
    exe_name = f"{name}.exe" if os.name == "nt" else name
    candidate = Path(sys.executable).parent / exe_name
    if candidate.exists():
        return str(candidate)

    on_path = shutil.which(name)
    if on_path:
        return on_path

    return name  # let subprocess.run raise FileNotFoundError, handled by the caller
