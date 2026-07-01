# AGENTS.md

## Project Context

Illusion Lab is a collection of independent visual illusion experiments. Each numbered directory should remain self-contained unless shared tooling is clearly useful across projects.

The project does not have a fixed technology stack. Choose rendering, animation, interaction, and test tools per experiment based on the illusion being built, and do not describe any single rendering library as the repository-level stack.

Core illusion target to keep in mind for future work: Depth-ambiguous bistable rotation illusion.

## Development Notes

- Prefer the existing workspace scripts in the root `package.json` for build, test, preview, and dev tasks.
- Keep project documentation focused on the illusion goal, user-facing behavior, commands, and local file structure.
- When adding a new experiment, use the numbered `00N-short-name/` directory pattern and keep source, tests, package metadata, and config inside that directory.
