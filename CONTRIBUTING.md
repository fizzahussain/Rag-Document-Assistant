# Contributing to RAG Document Assistant

Thank you for considering contributing to the RAG Document Assistant project!

## Branching Strategy

We follow a feature-branch development model:
- `main`: Production-ready, stable releases.
- `develop`: Primary integration branch.
- Feature branches: `feature/<short-description>`, `fix/<short-description>`, `docs/<short-description>`, `test/<short-description>`.

## Commit Messages

We strictly adhere to [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Adding or updating tests
- `refactor:` Code refactoring without functionality changes
- `ci:` Continuous integration changes
- `chore:` Maintenance tasks

## Pull Request Checklist

Before submitting a Pull Request:
1. Ensure all unit and integration tests pass (`python -m pytest`).
2. Run formatting and linting tools (`ruff check .` and `mypy .`).
3. Ensure no `.env` files or secrets are committed.
4. Fill out the complete Pull Request template.
