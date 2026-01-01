<!--
Version change: 1.0.0 -> 1.1.0
List of modified principles:
  - PRINCIPLE_1_NAME: Safety First (Backups & Validation) (Unchanged)
  - PRINCIPLE_2_NAME: CLI-First Automation (Unchanged)
  - PRINCIPLE_3_NAME: Identity Precision (Hashing) (Unchanged)
  - PRINCIPLE_4_NAME: Spec-Driven Development (SDD) (New - replaced Transparency/Privacy)
  - PRINCIPLE_5_NAME: Continuous Quality (Linting & Hooks) (New - replaced Speckit Workflow Discipline)
Added sections:
  - Project Purpose
  - Merge Strategy (within Development Workflow)
Removed sections:
  - Transparency and Privacy (Point IV)
Templates requiring updates:
  - ✅ updated: .specify/templates/plan-template.md
  - ✅ updated: .specify/templates/spec-template.md
  - ✅ updated: .specify/templates/tasks-template.md
Follow-up TODOs:
  - Initialize pre-commit hooks and ruff configuration.
-->

# Little Snitch Rule Manager Constitution

## Project Purpose
The Little Snitch Rule Manager is a utility designed to provide a safe, automated, and precision-focused interface for managing Little Snitch rules. It specifically addresses the challenges of maintaining network security policies for frequently updated binaries (e.g., via Homebrew) on macOS, ensuring that rule integrity is maintained through cryptographic verification.

## Core Principles

### I. Safety First (Backups & Validation)
Every modification to the Little Snitch configuration MUST be preceded by a persistent, timestamped backup. Validation of the configuration model after restoration is mandatory; if restoration fails, the system MUST automatically attempt to revert to the most recent known-good backup.

### II. CLI-First Automation
All functionality MUST be exposed via a non-interactive CLI interface supporting standard I/O (stdin/args -> stdout). This ensures the tool can be safely integrated into automated system hooks, such as Homebrew post-update scripts, without requiring manual terminal intervention.

### III. Identity Precision (Hashing)
Rules and code requirements MUST be tied to the resolved binary hash (`fileHash`) rather than just paths or developer certificates where possible. This prevents security gaps caused by binary updates that would otherwise break existing rules or allow unauthorized binary execution.

### IV. Spec-Driven Development (SDD)
Development MUST be driven by formal specifications. No implementation should begin without a peer-reviewed (or AI-validated) Specification and Implementation Plan. This ensures that features are built against clear requirements and that the resulting code is testable and maintainable.

### V. Continuous Quality (Linting & Hooks)
All code MUST adhere to the project's linting and formatting standards (e.g., Ruff). Quality checks MUST be enforced via git commit hooks (pre-commit) to prevent substandard code from entering the repository history.

### VI. Reproducibility and Dependency Integrity
Every tool, library, or utility used in the development or execution of the project MUST be explicitly declared in the project's dependency management file (`pyproject.toml`). The environment MUST be fully reproducible from a fresh clone using only declared dependencies; "global" or "system-wide" tool assumptions are prohibited.

## Technical Constraints

- **Platform**: MUST target macOS (Darwin) exclusively.
- **Runtime**: MUST use Python 3.11+ as the primary scripting engine.
- **Privileges**: Interactions with the Little Snitch CLI (`littlesnitch`) require `sudo` elevation.
- **Backups**: Backups MUST be stored in a persistent user directory (`~/.ls_backups`).

## Development Workflow

- **Branching**: Feature branches MUST use the `NNN-short-description` format (e.g., `001-add-logging`).
- **Merge Strategy**: Feature branches MUST be merged back into `main` using the `--no-ff` (no-fast-forward) method to preserve a clear history of feature integration.
- **Tooling**: Use `specify` and `speckit` commands for all workflow orchestration. 
- **Commits**: Follow conventional commits (e.g., `feat:`, `fix:`, `docs:`, `chore:`).

## Governance

- **Supremacy**: This Constitution supersedes all other project documentation and practices.
- **Amendments**: Any change to these principles requires a version bump and an update to the "Sync Impact Report."
- **Versioning**: 
  - MAJOR: Removal or redefinition of a core principle.
  - MINOR: New principle/section added or materially expanded guidance.
  - PATCH: Clarifications, wording, typo fixes, non-semantic refinements.

**Version**: 1.2.0 | **Ratified**: 2025-12-31 | **Last Amended**: 2025-12-31
