# AI Agent System Documentation

> **Status: historical.** This document describes a development-agent pipeline
> — `agents/dev/`, `workflows/pipeline.py` — that is no longer part of the
> backend. The `agents/dev/` package was removed, so `workflows/pipeline.py`
> can no longer be imported; the rule engine it used (`rules/`) is still live
> and is exercised by the test suites.
>
> The agent system that serves the product — query analysis and the routing
> between RAG and tools — is documented in
> [agent-system.md](./agent-system.md).

## Overview
The AI Agent System is a comprehensive framework designed to automate development tasks within the Real Estate Assistant project. It leverages specialized autonomous agents to handle coding, debugging, testing, and documentation.

## Architecture

### 1. Agents (`agents/dev/`)
The system consists of specialized agents inheriting from `DevAgent`:
- **CodingAgent**: Generates clean, type-hinted Python code.
- **DebuggingAgent**: Analyzes errors and provides fixes.
- **TestingAgent**: Generates `pytest` unit tests.
- **DocumentationAgent**: Creates Markdown documentation.

### 2. Rule Engine (`rules/`)
Ensures code quality and security before code is accepted.
- **Quality**: Checks line length, naming conventions (stub).
- **Security**: Scans for hardcoded secrets.
- **Performance**: Checks for inefficient patterns (e.g., string concatenation in loops).

### 3. Workflow Orchestrator (`workflows/pipeline.py`)
Manages the end-to-end process:
1.  **Feature Request** -> CodingAgent
2.  **Code** -> RuleEngine (Validation)
3.  **Valid Code** -> TestingAgent
4.  **Valid Code** -> DocumentationAgent
5.  **Result** -> Final Package

## Configuration
Agents are configured via `DevPipeline` initialization, which defaults to using the `openai` provider via `ModelProviderFactory`.

## Usage

### Programmatic Usage
```python
from workflows.pipeline import DevPipeline

pipeline = DevPipeline()
result = pipeline.implement_feature("Create a function to calculate mortgage monthly payments")

if result["status"] == "success":
    print("Code:", result["final_output"]["code"])
    print("Tests:", result["final_output"]["tests"])
```

## Troubleshooting
- **LLM Connection Errors**: Ensure `OPENAI_API_KEY` or relevant provider keys are set in `.env`.
- **Validation Failures**: Check `result["steps"]` for violation details.
