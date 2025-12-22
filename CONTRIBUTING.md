# Contributing to Hedera Agent Kit (Python)

We are thrilled that you're interested in contributing to the **Hedera Agent Kit**! Whether it's a simple doc fix or a major feature, we appreciate your help.

---

## 1. Getting Started

1. **Fork** the repository.
2. **Clone** your fork:

```bash
git clone https://github.com/<your-github-username>/hedera-agent-kit-py.git
```

3. **Set up the development environment**:

```bash
cd hedera-agent-kit-py/python
poetry install
```

4. Create a new branch for your work:

```bash
git checkout -b feat/your-feature-name
```

5. Make your changes, write or update tests as needed, and commit with a DCO sign-off (details below).
6. Push your branch to GitHub and open a pull request (PR) against `main`.

---

## 2. Developer Certificate of Origin (DCO)

This project requires DCO sign-offs. When you commit, include a line in your commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

If you use the CLI, you can add the `-s` or `--signoff` flag:

```bash
git commit -s -m "Implement a new feature"
```

Make sure the name and email match the identity you've set in Git. GitHub Actions will verify DCO compliance on every PR. If you forget, you can amend your commit or force-push once you've added the sign-off line.

---

## 3. Code Style & Testing

### Linting & Formatting

This project uses **Ruff** for linting and **Black** for code formatting.

To check for linting issues:

```bash
poetry run ruff check .
```

To check formatting without making changes:

```bash
poetry run black --check .
```

To auto-fix formatting issues:

```bash
poetry run black .
```

### Testing

Ensure all tests pass locally:

```bash
# Run unit tests
poetry run pytest test/unit

# Run integration tests (requires Hedera testnet credentials)
poetry run pytest test/integration

# Run all tests
poetry run pytest
```

### Type Checking

We use type hints throughout the codebase. While not strictly enforced, please add type annotations to new code.

---

## 4. How to Contribute

### Create an Issue Requesting Toolkit Features

[Open an issue](https://github.com/hashgraph/hedera-agent-kit-py/issues/new?template=toolkit_feature_request.yml&labels=feature-request) in the hedera-agent-kit-py repository.

### Find a Task

- Check out our Roadmap or look for open Issues in the repository.
- We use labels like `good-first-issue`, `help-wanted`, and `enhancement` to help identify tasks.

### Submit a Pull Request

1. Open a PR on GitHub, linking it to the relevant Issue if applicable.
2. The PR will run automated checks (lint, test, DCO).
3. Once approved, a maintainer will merge it. We'll thank you for your contribution!

---

## 5. Contribution Examples

### Create a Different Tool Calling Agent with Another LLM

Using `python/examples/langchain/plugin_tool_calling_agent.py` as a template, create a new file `python/examples/langchain/plugin_tool_calling_agent_anthropic.py`:

```python
# Change import
from langchain_anthropic import ChatAnthropic

# Change LLM initialization
llm = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    temperature=0,
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)
```

Update `pyproject.toml` dependencies:

```toml
[tool.poetry.dependencies]
langchain-anthropic = "^0.x.x"
```

Update `.env` file:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### Add a New Tool

1. Create a new tool file in the appropriate plugin directory (e.g., `hedera_agent_kit/plugins/core_token_plugin/`)
2. Define the parameter schema in `hedera_agent_kit/shared/parameter_schemas/`
3. Add parameter normalization logic in `hedera_agent_kit/shared/parameter_normaliser.py`
4. Register the tool in the plugin's `__init__.py`
5. Write tests:
   - Unit tests in `test/unit/`
   - Integration tests in `test/integration/`
   - E2E tests in `test/e2e/`
   - Tool matching tests in `test/tool_matching_tests/`

---

## 6. Community & Support

- Use GitHub to propose ideas and [open an issue](https://github.com/hashgraph/hedera-agent-kit-py/issues/new?template=toolkit_feature_request.yml&labels=feature-request) or ask questions.
- [Join the Hedera Discord Server](https://discord.gg/hedera) and reach out in the appropriate channel.

---

Thank you for helping make the Hedera Agent Kit better!
