"""Custom exceptions for service layer."""


class ServiceError(Exception):
    """Base exception for all service-related errors."""

    pass


class DockerServiceError(ServiceError):
    """Exception raised for Docker service operations."""

    pass


class GitServiceError(ServiceError):
    """Exception raised for Git service operations."""

    pass


class ImageNotFoundError(DockerServiceError):
    """Exception raised when a Docker image is not found."""

    pass


class ContainerNotFoundError(DockerServiceError):
    """Exception raised when a Docker container is not found."""

    pass


class BranchNotFoundError(GitServiceError):
    """Exception raised when a Git branch is not found."""

    pass