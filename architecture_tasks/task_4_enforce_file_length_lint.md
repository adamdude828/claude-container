# Task 4 – Enforce Maximum File Length Through Linting & CI

**Problem**
The presence of a 1,500-line module (`task.py`) indicates that file size guidelines are not enforced. Large files hinder readability and discourage modular design.

**Goal**
Introduce automated checks that fail CI when a Python source file exceeds a defined line-count threshold (e.g. 400 lines).

**Proposed Approach**
1. Adopt **`ruff`** (already in cache) or **`flake8`** with the `flake8-length` plugin.
2. Configure the limiter in `pyproject.toml`, e.g.
   ```toml
   [tool.ruff]
   # … existing config …
   line-length = 120  # existing style
   allowed-py-codemod = []
   max-lines-per-file = 400
   ```
   or for flake8:
   ```ini
   [flake8]
   max-line-length = 120
   max-lines = 400
   ```
3. Update GitHub Actions / local `scripts/test.sh` to run `ruff check` (or `flake8`) and fail if violations are found.
4. Provide a `tox` environment or `nox` session for easy local execution.
5. Add documentation in `README.md` on the new rule and how to disable it temporarily (with proper justification) via `# noqa: E501` or similar.

**Acceptance Criteria**
- CI pipeline fails when any `.py` file >400 lines.
- Existing files are either refactored (Task 1–3) or explicitly exempted with justification comments.
- Developers can run `poetry run ruff check` to validate locally. 