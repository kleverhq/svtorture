# Script guidance

## Source of truth

- Stable invocation surface: root `justfile`
- Workflow callers: `../.github/workflows/`
- Automation architecture: `../docs/architecture.md`

## Local guidance

- Keep scripts deterministic, non-interactive, and safe for CI.
- Each module header must explain what the script does, why it exists, who calls it, and what it produces.
- Prefer adding a `just` recipe or workflow call over making a script path a public interface.
