# Task 6 – Dynamic MCP Server Registration & Selection for Tasks

**Problem**
Current `task create` and `task continue` commands run Claude inside the Docker container with a single, hard-coded MCP server configuration. As we adopt more MCP servers (e.g. Context7 + team-local orchestrators) we need a flexible way to:
1. Register 1‒N MCP servers with *claude-container* once.
2. Choose which subset of those servers is made available to a given task run.
3. Materialise the chosen servers into a `.mcp.json` file inside the task container **before** invoking the Claude CLI.

**Goal**
Enable developers to manage multiple MCP servers and dynamically inject the desired configuration when starting or continuing a task, without manual file tweaking.

---

## Design Overview
1. **Project-local MCP registry (untracked)**  
   • A JSON file – e.g. `.claude-container/mcp.json` under the repo root – stores all known MCP servers **for this clone**.  
   • This directory (`.claude-container/`) is already listed in `.gitignore`, so no additional ignore rules are needed.  
   • Format still matches [Anthropic docs](https://docs.anthropic.com/en/docs/claude-code/tutorials#set-up-model-context-protocol-mcp).  
   • Example:
   ```json
   {
     "mcpServers": {
       "context7": { "type": "stdio", "command": "npx", "args": ["-y", "@upstash/context7-mcp"] },
       "telemetry": { "type": "http", "url": "https://mcp.mycorp.dev" }
     }
   }
   ```

2. **CLI for MCP management**  
   New top-level verbs under `claude-container mcp`:
   • `list` – show registered servers  
   • `add <name> <json|file>` – append/update entry  
   • `remove <name>` – delete entry  
   • (Optional) `validate` – ping server / run health check.

3. **Task commands accept `--mcp` flag**  
   • `claude-container task create --mcp context7,telemetry "Implement X"`  
   • `claude-container task continue <task-id> --mcp context7`  
   • If flag omitted default to *all* servers in `.mcp.json` (maintains current behaviour).

4. **Dynamic file generation inside container**  
   • During task startup the selected subset is serialised to `/workspace/.mcp.json` (same dir as code) using `docker exec echo > file`.  
   • We **do not** mount host file to avoid leaking unrelated servers into sandbox.

5. **Data persistence**  
   • Selected server list is stored in task metadata so continuations inherit previous choice unless overridden.

6. **Fallback to Claude CLI flags**  
   If Anthropic adds `claude --mcp-server context7`, we can switch implementation to CLI flags instead of file ‑ design keeps this pluggable.

---

## Implementation Steps
1. **Schema & Constants**  
   • Add `MCP_CONFIG_PATH = ".mcp.json"` constant.  
   • Create `claude_container/models/mcp.py` with pydantic model for file.

2. **MCP Manager Utility**  
   • `claude_container/utils/mcp_manager.py` to load/save/validate registry.  
   • Exposed functions: `load_registry(root)`, `filter_registry(reg, names)`.

3. **CLI Commands**  
   • New Click group `cli/commands/mcp/` implementing `list`, `add`, `remove`.  
   • Use [`questionary`](https://github.com/tmbo/questionary) for interactive multi-select prompts (integrates cleanly with Click).  
   • Unit tests in `tests/cli/test_mcp_*.py`.

4. **Extend Task Create / Continue**  
   • Add `--mcp` option (comma-sep).  
   • Behaviour:
      1. If `--mcp` provided → use list.
      2. Else if TTY **interactive** → present `questionary.checkbox` prompt allowing user to pick 1+ servers.
      3. Else (non-TTY, piped, CI) → default to **all** servers.  
   • On startup:
     ```python
     registry = load_registry(project_root)
     selected = filter_registry(registry, mcp_names)
     write_mcp_json(container, selected)
     ```
   • Persist `mcp_names` in task record (`TaskMetadata` new field `mcp_servers: List[str]`).

5. **Write helper to container**  
   • `ContainerRunner.write_file(path, content)` convenience.  
   • Use above to write `.mcp.json`.

6. **Docs & Examples**  
   • Update `README.md` + `CLAUDE.md` with usage examples.

7. **CI & Lint**  
   • Add tests ensuring `.mcp.json` is present inside running container with correct subset.  
   • Ensure total file length < 400 lines 🙂 (satisfy Task 4 linter).

---

## Acceptance Criteria (updated)
- If `--mcp` flag is supplied its value is honoured verbatim.
- If the flag is omitted **and** the command is running in an interactive TTY, the user is prompted with a multi-select list of available servers (powered by `questionary`).  Choosing "all" selects every server quickly.
- If the flag is omitted **and** STDIN/STDOUT is non-interactive (e.g. CI), all servers are selected automatically.
- `claude-container mcp list` shows all servers from project root `.claude-container/mcp.json`.
- Running `claude-container task create --mcp context7` produces `.mcp.json` **inside** the task container containing only `context7` config.
- Omitting flag defaults to all servers.
- Task metadata records `mcp_servers` so subsequent `task continue` inherits automatically.
- Unit tests cover registry parsing, prompt logic, CLI flags, and container file write.
- Documentation updated.

---

## Open Questions
1. Where should `.mcp.json` live inside container – `/workspace` vs. `$HOME`? Docs suggest project root; we'll use `/workspace` unless spec changes.
2. Do we need per-developer overrides (e.g., personal servers)? Could load `~/.claude_container/mcp.json` and merge.
3. Health checking of MCP servers – out of scope for MVP but CLI `validate` could be future work.

---

## Estimated Effort
- Core implementation: **4-6 hrs**
- CLI & tests: **3 hrs**
- Docs & polish: **1 hr**

_Total: ~1 working day._ 