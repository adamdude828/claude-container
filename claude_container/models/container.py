"""Container configuration models."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RuntimeVersion(BaseModel):
    """Runtime version configuration."""
    name: str
    version: str


class ContainerConfig(BaseModel):
    """Container configuration for a project."""
    env_vars: Dict[str, str] = Field(default_factory=dict)
    runtime_versions: List[RuntimeVersion] = Field(default_factory=list)
    custom_commands: List[str] = Field(default_factory=list)
    base_image: str = "node:20"
    include_code: bool = False
    cached_image_tag: Optional[str] = None
    customized: bool = False
    customized_at: Optional[str] = None