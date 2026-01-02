# **ADR 0000: Tech Stack for Hedera Agent Kit (Python SDK)**

**Date:** 2025-10-20
**Context:** Python-based implementation of the Hedera Agent Kit, designed for AI agent integration and natural-language
interaction with Hedera network services.

---

## **1. Context and Goal**

The goal is to establish a **modern, consistent, and maintainable tech stack** for developing the Python SDK (
`hedera-agent-kit-py`) that mirrors the TypeScript version’s modularity, reliability, and developer experience.

This ADR captures decisions regarding:

* Package and dependency management
* Code quality and formatting
* Typing, testing, and CI/CD integration
* Documentation and versioning strategy

---

## **2. Decisions**

### **2.1 Project Manager**

**Options:** `Poetry` vs `Hatch`
**Decision:** ✅ **Poetry**

**Rationale:**

* Mature and widely adopted in the Python ecosystem.
* Handles dependency management, builds, publishing, and virtual environments in one tool.
* Provides reproducible environments via lockfiles.
* Compatible with plugins like `poetry-dynamic-versioning`.

**Reference:** [https://python-poetry.org/](https://python-poetry.org/)

---

### **2.2 Package Manager**

**Decision:** ✅ **Poetry (uses pip internally)**

**Rationale:**

* Poetry manages dependencies via `pyproject.toml` and integrates seamlessly with virtual environments.
* While `uv` offers faster installs, its integration with Poetry is non-trivial and unnecessary for the project’s scale.

**Reference:** [https://python-poetry.org/](https://python-poetry.org/)

---

### **2.3 Testing Framework**

**Decision:** ✅ **PyTest + pytest-cov**

**Rationale:**

* PyTest is the most popular testing framework for Python projects.
* `pytest-cov` integrates cleanly for test coverage reporting in CI/CD.

**Reference:** [https://docs.pytest.org/en/stable/](https://docs.pytest.org/en/stable/)

---

### **2.4 Environment Variable Manager**

**Decision:** ✅ **python-dotenv**

**Rationale:**

* Simple and reliable environment management via `.env` files.
* Widely compatible with Poetry environments and deployment pipelines.

**Reference:** [https://pypi.org/project/python-dotenv/](https://pypi.org/project/python-dotenv/)

---

### **2.5 Code Formatter**

**Decision:** ✅ **Black**

**Rationale:**

* Industry-standard formatter for Python, opinionated and zero-config.
* Ensures consistent style across contributors.
* Added as a **pre-commit hook** for enforcement.

**Reference:** [https://black.readthedocs.io/en/stable/](https://black.readthedocs.io/en/stable/)

---

### **2.6 Code Linter**

**Decision:** ✅ **Ruff**

**Rationale:**

* Modern, fast Rust-based linter.
* Replaces and extends `flake8` and `pylint` functionality.
* Configurable via `pyproject.toml` and integrates with pre-commit.

**Reference:** [https://docs.astral.sh/ruff/](https://docs.astral.sh/ruff/)

---

### **2.7 Typing Support**

**Decision:** ✅ **MyPy + typing (stdlib)**

**Rationale:**

* `typing` is part of the Python standard library since 3.5.
* `MyPy` serves as the static type checker to enforce type safety.
* Provides early error detection and IDE integration.

**Reference:** [https://mypy.readthedocs.io/en/stable/](https://mypy.readthedocs.io/en/stable/)

---

### **2.8 Pre-Commit Hooks**

**Decision:** ✅ **pre-commit**

**Rationale:**

* Git hook framework that ensures code quality before commits.
* Equivalent to `husky` for TypeScript projects.
* Runs Black, Ruff, and MyPy automatically before code is committed.

**Reference:** [https://pre-commit.com/](https://pre-commit.com/)
---

### **2.9 Documentation Framework**

**Decision:** ❌ **None for now**

**Rationale:**

* The SDK is still evolving; documentation will be generated later.
* **Future options:** `Sphinx` (for auto docstring parsing) or `MkDocs` (for static site generation).

---

### **2.10 Versioning**

**Decision:** ✅ **poetry-dynamic-versioning**

**Rationale:**

* Automatically generates semantic versions from Git tags.
* Avoids manual version bumps in `pyproject.toml`.
* Works well with GitHub Actions for automated releases.

**Reference:**
1. [https://pypi.org/project/poetry-dynamic-versioning/](https://pypi.org/project/poetry-dynamic-versioning/)
2. [https://mestrak.com/blog/semantic-release-with-python-poetry-github-actions-20nn](https://mestrak.com/blog/semantic-release-with-python-poetry-github-actions-20nn)

### 2.11 CI/CD Integration

**Decision:**  ✅ **Implement GitHub Actions CI/CD Pipeline**

**Rationale:**

* Provides automatic testing and linting on every push and pull request.
* Ensures consistent formatting, linting, typing, and test coverage enforcement.
* Enables automated package build validation and (future) publishing to PyPI.
* Workflow Location: `.github/workflows/ci.yml`

Workflow Includes:

* Python setup with Poetry dependency cache
* Ruff lint check
* Black format check
* MyPy strict type check
* PyTest tests execution
* Poetry build verification

**Reference:** [https://docs.github.com/en/actions/learn-github-actions/introduction-to-github-actions](https://docs.github.com/en/actions/learn-github-actions/introduction-to-github-actions)

---

## **3. Summary of Key Decisions**

| Category         | Decision                     | Tool |
|------------------|------------------------------|------|
| Project Manager  | Poetry                       | ✅    |
| Package Manager  | Poetry                       | ✅    |
| Testing          | PyTest + pytest-cov          | ✅    |
| Env Vars         | python-dotenv                | ✅    |
| Formatter        | Black                        | ✅    |
| Linter           | Ruff                         | ✅    |
| Typing           | MyPy                         | ✅    |
| Pre-Commit Hooks | pre-commit                   | ✅    |
| Documentation    | None (Future: Sphinx/MkDocs) | ❌    |
| Versioning       | poetry-dynamic-versioning    | ✅    |
| CI CD            | github actions               | ✅    |
