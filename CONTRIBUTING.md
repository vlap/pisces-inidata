# Contributing to pisces-inidata

Thank you for your interest in contributing to `pisces-inidata`! This project provides open, reproducible biogeochemical initial condition generation for the PISCES model and EC-Earth4.

## Code of Conduct
We are committed to providing a welcoming, inclusive, and collaborative environment. Please maintain professional, constructive discourse.

## Development Workflow
1. **Fork and Clone**:
   ```bash
   git clone https://github.com/vlap/pisces-inidata.git
   cd pisces-inidata
   ```
2. **Environment Setup**:
   Ensure you have CDO (>= 2.0), NCO, and Python (>= 3.10) installed:
   ```bash
   pip install -e ".[dev,docs]"
   ```
3. **Branching**:
   Create a descriptive feature branch:
   ```bash
   git checkout -b feature/my-new-tracer
   ```
4. **Code Standards**:
   - Follow PEP 8 for Python code.
   - Run `flake8` and `pytest tests/` before submitting.
   - Bash scripts should pass `shellcheck` and maintain modular architecture.
   - Follow YAGNI and DRY principles: simple, flat code; native standard library operations; fail-fast error checking.
   - Document any shortcuts explicitly: `# shortcut: explanation`.
5. **Documentation**:
   If adding features or data sources, update the relevant pages in `docs/` and verify the build:
   ```bash
   sphinx-build -W -b html docs docs/_build/html
   ```
6. **Submitting Changes**:
   Push to your fork and submit a Pull Request describing the changes, tests executed, and scientific references for new datasets.
