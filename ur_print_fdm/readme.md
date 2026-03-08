# ur-print-fdm

PyQt6 desktop application for Universal Robots printing workflows.

## Install

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.11 -m pip install -U pip
py -3.11 -m pip install -e .[dev]
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
- New code should import configuration from `ur_print_fdm.config`, not from legacy shim modules.
