# Architecture Improvement Tasks

Below is a high-level list of proposed architecture improvements discovered while reviewing the current code-base. Each task is described in its own markdown file inside this directory.

| # | Task | Primary Files Affected | Link |
|---|------|-----------------------|------|
| 1 | Refactor the huge `task.py` CLI command into smaller modules | `claude_container/cli/commands/task.py` | [task_1_refactor_cli_task_command.md](task_1_refactor_cli_task_command.md) |
| 2 | Extract shared CLI utilities into a reusable helper package | `claude_container/cli/commands/*`, `claude_container/cli/main.py` | [task_2_extract_cli_utilities.md](task_2_extract_cli_utilities.md) |
| 3 | Introduce a service layer for Docker & Git operations | `claude_container/core/container_runner.py`, `claude_container/core/docker_client.py`, CLI commands | [task_3_service_layer_for_docker_and_git.md](task_3_service_layer_for_docker_and_git.md) |
| 4 | Enforce maximum file length through linting and CI | Whole repo | [task_4_enforce_file_length_lint.md](task_4_enforce_file_length_lint.md) |
| 5 | Add architecture documentation & diagrams | Docs | [task_5_architecture_docs.md](task_5_architecture_docs.md) |

Follow the links for detailed description, rationale, and acceptance criteria for each task. 