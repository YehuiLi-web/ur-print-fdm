# Manual Checks

This folder contains manual verification scripts that used to live at the repo root as `test_*.py` files.

They are intentionally kept out of automated pytest collection because they usually require one or more of the following:

- a running URSim or physical robot
- manual UI observation
- local environment-specific devices or network access

Run them manually when you need targeted integration checks.
