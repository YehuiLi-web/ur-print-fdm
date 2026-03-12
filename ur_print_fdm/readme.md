# ur-print-fdm

PyQt6 desktop application for Universal Robots printing workflows.

## Install

Run the install commands from the repository root, not from this `ur_print_fdm/` folder.

Runtime only:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install -U pip
py -3.11 -m pip install -r requirements.txt
```

Development:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install -U pip
py -3.11 -m pip install -r requirements-dev.txt
```

## Run

```powershell
.\.venv\Scripts\Activate.ps1
py -3.11 -m ur_print_fdm
```

## Test

```powershell
.\.venv\Scripts\Activate.ps1
py -3.11 -m pytest -q
```

## Notes

- Automated tests live in `ur_print_fdm/tests`.
- Manual robot or UI verification scripts live in the workspace `manual_checks/` directory.
- The canonical dependency list now lives in the repository-root `pyproject.toml`.
- New code should import configuration from `ur_print_fdm.config`, not from legacy shim modules.
