# Task 5 – Add Architecture Documentation & Diagrams

**Problem**
The project lacks a centralised architectural overview. New contributors must read the source code to understand interactions between CLI, core services, models, and external dependencies. Clear documentation accelerates onboarding and reduces architectural drift.

**Goal**
Produce up-to-date, visual and textual documentation of the system's architecture and make it easily accessible.

**Proposed Deliverables**
1. **`docs/architecture_overview.md`** – high-level description of application layers (CLI, Services, Core, External).
2. **Component diagram** – Mermaid chart embedded in doc to illustrate module boundaries and data flow.
3. **ADR (Architecture Decision Records) template** plus first ADR documenting the decision to adopt the new service layer (Task 3).
4. **`CONTRIBUTING.md`** section linking to architecture docs.

**Suggested Mermaid Example**
```mermaid
graph TD
  subgraph CLI
    task_cmd[Task Commands]
    build_cmd[Build Commands]
  end

  subgraph Services
    docker_srv[DockerService]
    git_srv[GitService]
    claude_srv[ClaudeService]
  end

  subgraph Core
    container_runner[ContainerRunner]
    task_storage[TaskStorageManager]
  end

  task_cmd --> docker_srv
  task_cmd --> git_srv
  docker_srv --> container_runner
  git_srv --> container_runner
  container_runner --> claude_srv
  task_cmd --> task_storage
```

**Acceptance Criteria**
- Docs live under `docs/` and render correctly on GitHub.
- Diagrams render without additional plugins.
- ADR template exists; first ADR committed.
- A reader can grasp system architecture within 10 minutes using the docs. 