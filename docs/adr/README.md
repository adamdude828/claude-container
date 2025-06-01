# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the Claude Container project.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences. ADRs help us:

- Document why decisions were made
- Understand the trade-offs considered
- Learn from past decisions
- Onboard new team members

## ADR Index

- [000 - ADR Template](000-adr-template.md) - Template for new ADRs
- [001 - Service Layer Abstraction](001-service-layer-abstraction.md) - Introduction of service layer for Docker and Git operations

## Creating a New ADR

1. Copy the template: `cp 000-adr-template.md 00X-brief-description.md`
2. Fill in all sections of the template
3. Update this README with a link to the new ADR
4. Submit a PR with the new ADR

## ADR Status Values

- **proposed**: The decision is still under discussion
- **accepted**: The decision has been accepted and implemented
- **rejected**: The decision was rejected
- **deprecated**: The decision is no longer relevant
- **superseded**: The decision has been replaced by another ADR