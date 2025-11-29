# Agent instructions for `back`

This FastAPI service is designed for container-only usage with uv-based packaging.
Follow these guidelines when working inside the `back` directory tree:

- Keep code PEP 8 compliant with a 100-character line limit and Pylance strict-mode friendliness.
- Do not add `try/except` around imports or use string trimming helpers (e.g., `.strip`).
- Prefer explicit type checks and raise errors when required fields are missing instead of fallback logic.
- Maintain the existing DDD-ish layout (`api`, `domain`, `data`) and avoid cross-file nesting of functions.
- Assume commands are executed inside Docker; mirror uv tooling already used in this service.
