# Introduce Service Layer for Docker and Git Operations

## Status

accepted

## Context

The Claude Container project initially had Docker and Git operations spread across multiple command files, with direct calls to `DockerClient` and command-line git operations. This led to:

- Code duplication across commands
- Inconsistent error handling
- Tight coupling between CLI and low-level operations
- Difficulty in testing command logic
- No clear separation of concerns

The codebase needed better organization to support future growth and maintainability.

## Decision

We introduced a service layer (`claude_container/services/`) that acts as an intermediary between the CLI commands and core functionality. This layer encapsulates:

1. **DockerService**: All Docker-related operations including container management, image building, and cleanup
2. **GitService**: Git and GitHub CLI operations for version control and PR creation

The service layer provides a clean, high-level API that CLI commands can use without knowing implementation details.

## Consequences

### Positive

- **Improved testability**: Services can be easily mocked in command tests
- **Code reusability**: Common operations are centralized in services
- **Consistent error handling**: Services provide uniform error handling patterns
- **Better separation of concerns**: CLI focuses on user interaction, services handle business logic
- **Easier maintenance**: Changes to Docker/Git operations only require service updates
- **Future flexibility**: Services can be extended without changing command interfaces

### Negative

- **Additional abstraction layer**: One more layer to understand and maintain
- **Initial refactoring effort**: Required updating all existing commands
- **Potential over-engineering**: For simple operations, the service layer might seem excessive

### Neutral

- **Learning curve**: New contributors need to understand the service layer pattern
- **File organization**: More directories and files to navigate
- **Dependency injection**: Commands now depend on service instances

## Options Considered

### Option 1: Keep direct Docker/Git calls in commands

Continue with the existing pattern where commands directly use `DockerClient` and subprocess for git.

**Pros:**
- Simpler for very basic operations
- Less abstraction to understand
- Direct control over operations

**Cons:**
- Code duplication across commands
- Harder to test command logic
- Inconsistent error handling
- Tight coupling makes changes difficult

### Option 2: Introduce service layer (chosen)

Create dedicated service classes that encapsulate Docker and Git operations.

**Pros:**
- Clean separation of concerns
- Improved testability
- Consistent API for commands
- Easier to add new features
- Better code organization

**Cons:**
- Additional abstraction layer
- More files to maintain
- Initial refactoring effort

### Option 3: Use repository pattern

Implement a full repository pattern with interfaces and implementations.

**Pros:**
- Maximum flexibility
- Easy to swap implementations
- Very testable

**Cons:**
- Over-engineering for current needs
- Too much abstraction
- Increased complexity

## References

- [Architecture Overview](../architecture_overview.md)
- [Original Task Description](../../architecture_tasks/task_3_service_layer_for_docker_and_git.md)
- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)