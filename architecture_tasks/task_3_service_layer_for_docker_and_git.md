# Task 3 – Introduce Service Layer for Docker & Git Operations

**Problem**
`task.py` and other CLI commands directly orchestrate low-level Docker and Git calls (via `docker` Python SDK and `subprocess`). This leads to:

* Tight coupling between the CLI layer and infrastructure details.
* Scattered error-handling logic.
* Difficulty in stubbing external dependencies during testing.

**Goal**
Abstract Docker and Git interactions behind dedicated service classes so that callers can focus on *what* needs to be done instead of *how*.

**Proposed Components**
1. **`DockerService`** – wraps container & image lifecycle:
   * `build_image()`
   * `create_container()` / `exec()` / `remove_container()`
   * `image_exists()`
2. **`GitService`** – executes Git commands in a safe, logged manner:
   * `checkout_branch()`
   * `push_branch()`
   * `commit_all_changes(message)`
   * `branch_exists_local/remote()`
3. **`ClaudeService`** (optional) – encapsulates calls to the `claude` binary; consolidates streaming vs. polling behaviour.

Each service should:
* Live under `claude_container/services/`.
* Provide clear return types & raise custom exceptions on failure.
* Be injectable (pass into CLI modules) to facilitate mocking.

**Migration Plan**
1. Implement the new services alongside existing code.
2. Update the refactored CLI commands (Task 1) to depend on the service layer instead of direct `docker` / `subprocess` calls.
3. Gradually remove redundant code from `ContainerRunner` if functionality is superseded.
4. Add unit tests with mocks for both success & failure scenarios.

**Acceptance Criteria**
- CLI commands do not call `subprocess.*` or Docker SDK directly.
- All service methods are documented, typed, and covered by tests.
- Error messages surfaced to the user remain as helpful as before (or improve). 