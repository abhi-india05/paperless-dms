
import os
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def _candidate_venv_pythons():
    """Return possible project virtualenv Python executables in preference order."""
    return [
        BASE_DIR / '.venv' / 'Scripts' / 'python.exe',
        BASE_DIR / '.venv' / 'bin' / 'python',
    ]


def _find_venv_python():
    for candidate in _candidate_venv_pythons():
        if candidate.exists():
            return candidate
    return None


def _restart_with_venv_if_needed():
    venv_python = _find_venv_python()
    if not venv_python:
        return False

    current_executable = Path(sys.executable).resolve()
    if current_executable == venv_python.resolve():
        return False

    completed = subprocess.run(
        [str(venv_python), str(BASE_DIR / 'run.py'), *sys.argv[1:]],
        check=False,
    )
    raise SystemExit(completed.returncode)


def main():
    os.chdir(BASE_DIR)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'paperless_dms.settings')

    try:
        from django.core.management import execute_from_command_line
    except ModuleNotFoundError as exc:
        if exc.name == 'django' and _restart_with_venv_if_needed():
            return
        raise ImportError(
            'Django is not installed in the current Python interpreter. '
            'Use the project virtualenv at .venv or install Django there.'
        ) from exc

    if len(sys.argv) == 1:
        argv = ['manage.py', 'runserver', '127.0.0.1:8000']
    else:
        argv = ['manage.py', *sys.argv[1:]]

    execute_from_command_line(argv)


if __name__ == '__main__':
    main()