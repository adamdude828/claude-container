from pathlib import Path
from typing import Any


class EnvironmentDetector:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def detect(self) -> dict[str, Any]:
        """Detect project environment and requirements"""
        environment = {
            'base_image': 'ubuntu:22.04',
            'language': 'unknown',
            'package_manager': None,
            'framework': None,
            'dependencies': []
        }

        # Detect Python
        if self._has_file('pyproject.toml'):
            environment['language'] = 'python'
            if 'poetry' in self._read_file('pyproject.toml'):
                environment['package_manager'] = 'poetry'
        elif self._has_file('requirements.txt'):
            environment['language'] = 'python'
            environment['package_manager'] = 'pip'
        elif self._has_file('setup.py'):
            environment['language'] = 'python'
            environment['package_manager'] = 'pip'

        # Detect JavaScript/TypeScript
        elif self._has_file('package.json'):
            package_json = self._read_file('package.json')
            if self._has_file('tsconfig.json'):
                environment['language'] = 'typescript'
            else:
                environment['language'] = 'javascript'

            # Detect package manager
            if self._has_file('yarn.lock'):
                environment['package_manager'] = 'yarn'
            elif self._has_file('pnpm-lock.yaml'):
                environment['package_manager'] = 'pnpm'
            else:
                environment['package_manager'] = 'npm'

            # Detect framework
            if 'react' in package_json:
                environment['framework'] = 'react'
            elif 'vue' in package_json:
                environment['framework'] = 'vue'
            elif 'next' in package_json:
                environment['framework'] = 'nextjs'

        # Detect Rust
        elif self._has_file('Cargo.toml'):
            environment['language'] = 'rust'
            environment['package_manager'] = 'cargo'

        # Detect Go
        elif self._has_file('go.mod'):
            environment['language'] = 'go'
            environment['package_manager'] = 'go'

        # Detect Ruby
        elif self._has_file('Gemfile'):
            environment['language'] = 'ruby'
            environment['package_manager'] = 'bundler'

        # Detect Java
        elif self._has_file('pom.xml'):
            environment['language'] = 'java'
            environment['package_manager'] = 'maven'
        elif self._has_file('build.gradle') or self._has_file('build.gradle.kts'):
            environment['language'] = 'java'
            environment['package_manager'] = 'gradle'

        # Detect C/C++
        elif self._has_file('CMakeLists.txt'):
            environment['language'] = 'cpp'
            environment['package_manager'] = 'cmake'
        elif self._has_file('Makefile'):
            # Could be many languages, but assume C/C++
            content = self._read_file('Makefile').lower()
            if 'gcc' in content or 'g++' in content:
                environment['language'] = 'cpp'
            environment['package_manager'] = 'make'

        # Choose appropriate base image
        environment['base_image'] = self._select_base_image(environment)

        return environment

    def _has_file(self, filename: str) -> bool:
        """Check if file exists in project root"""
        return (self.project_root / filename).exists()

    def _read_file(self, filename: str) -> str:
        """Read file content"""
        filepath = self.project_root / filename
        if filepath.exists():
            try:
                return filepath.read_text()
            except:
                return ""
        return ""

    def _select_base_image(self, environment: dict[str, Any]) -> str:
        """Select appropriate base Docker image"""
        language = environment['language']

        if language == 'python':
            return 'python:3.11-slim'
        elif language in ['javascript', 'typescript']:
            return 'node:18'
        elif language == 'rust':
            return 'rust:latest'
        elif language == 'go':
            return 'golang:1.21'
        elif language == 'ruby':
            return 'ruby:3.2-slim'
        elif language == 'java':
            return 'openjdk:17-slim'
        elif language == 'cpp':
            return 'gcc:latest'
        else:
            return 'ubuntu:22.04'
