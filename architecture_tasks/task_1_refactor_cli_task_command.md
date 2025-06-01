# Task 1 – Refactor `task.py` CLI Command Into Smaller Modules

**Problem**
`claude_container/cli/commands/task.py` is ~1,500 lines long and contains logic for *all* task-related sub-commands. The file:

* Is hard to navigate and reason about.
* Mixes CLI parsing, business rules, Docker/Git orchestration, and presentation concerns.
* Makes unit–testing difficult because everything is tightly coupled.

**Goal**
Split `task.py` into dedicated, maintainable modules so that no single file exceeds ~300–400 lines.

**Proposed Approach**
1. Create a new package: `claude_container/cli/commands/task/` (directory with `__init__.py`).
2. For every sub-command currently implemented, add its own file, e.g.
   * `create.py`
   * `continue.py`
   * `list.py`
   * `show.py`
   * `delete.py`
   * …etc.
3. A thin `task/__init__.py` should expose a single `click.Group` that registers each sub-command from the sibling modules.
4. Extract reusable helper functions (e.g. `get_description_from_editor`, `get_feedback_from_editor`) into a *shared* `claude_container/cli/util.py` module so they can be imported by multiple commands.
5. Move heavy-weight orchestration logic (Docker + Git operations) into a service layer (see Task 3) and keep CLI files focused on argument parsing and presentation only.
6. Ensure backwards-compatibility for users; the entry-point `claude_container/cli/commands/__init__.py` should still expose the top-level `task` command group.

**Acceptance Criteria**
- No file in `cli/commands` exceeds 400 lines.
- Running `claude-container task <sub-command>` behaves exactly the same as before.
- All unit tests pass.
- New unit tests exist for at least the `create` and `continue` sub-commands.

**Risks & Mitigations**
- *Risk:* Refactor may introduce regressions.
  *Mitigation:* Add regression tests before refactor; leverage existing end-to-end test scripts.
- *Risk:* Import cycles while splitting helpers.
  *Mitigation:* Keep helper utilities free of heavy imports; inject dependencies where possible. 