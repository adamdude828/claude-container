# Task 2 – Extract Shared CLI Utilities Into Reusable Helper Package

**Problem**
The CLI command modules repeat a number of common actions:

* Authenticating with Claude (`check_claude_auth`).
* Acquiring the current project's root & data directories.
* Instantiating `TaskStorageManager`, `ContainerRunner`, etc.
* Rendering tables with `tabulate`.
* Prompting for editor-based input.

These concerns are duplicated in each sub-command, leading to boilerplate and potential inconsistencies.

**Goal**
Provide a small helper/utility layer that can be imported by all command modules to DRY up repetitive code and standardise behaviour.

**Proposed Approach**
1. Create `claude_container/cli/helpers/` with an `__init__.py` that re-exports helper functions.
2. Extract the following utilities:
   * `ensure_authenticated()`: wraps `check_claude_auth` and exits gracefully on failure.
   * `get_project_context()` → returns `(project_root, data_dir)` and performs validation.
   * `get_storage_and_runner()` → initialises `TaskStorageManager` and `ContainerRunner` from context.
   * `open_in_editor(template: str) -> str` → generalised editor launching logic (used by existing `get_description_from_editor`, etc.).
   * `print_table(headers, rows)` → thin wrapper around `tabulate` with project-wide defaults.
3. Update each splitted task command (Task 1) to import from the helper package.
4. Remove duplicated code in `build.py`, `run.py`, etc., and adopt the same helper where relevant.
5. Provide unit tests for each helper function; mock external dependencies (e.g. environment variables, subprocess).

**Acceptance Criteria**
- Zero code duplication of authentication/context initialisation across CLI modules.
- New helper functions are fully type hinted and documented.
- Unit tests achieve ≥90 % branch coverage for helper module.
- Overall CLI behaviour remains unchanged. 