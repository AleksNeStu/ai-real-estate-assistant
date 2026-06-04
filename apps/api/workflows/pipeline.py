"""
Workflow Orchestrator for Development Tasks.
"""

import logging
import re
import subprocess
import uuid
from typing import Any

from agents.dev.coding import CodingAgent
from agents.dev.documentation import DocumentationAgent
from agents.dev.testing import TestingAgent
from core.security_utils import sanitize_for_log
from rules.engine import RuleEngine

logger = logging.getLogger(__name__)

# Type alias for step results
StepResult = dict[str, Any]
PipelineResult = dict[str, Any]


class DevPipeline:
    def __init__(self, provider: str = "openai"):
        self.coding_agent = CodingAgent(provider=provider)
        self.testing_agent = TestingAgent(provider=provider)
        self.docs_agent = DocumentationAgent(provider=provider)
        self.rule_engine = RuleEngine()

    def _run_git_cmd(self, args: list[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error("Git command failed: %s", sanitize_for_log(e.stderr))
            return ""

    def create_feature_branch(self, description: str) -> str:
        """Create a new feature branch based on description."""
        # Create a slug from description
        slug = re.sub(r"[^a-z0-9]+", "-", description.lower()).strip("-")[:30]
        timestamp = uuid.uuid4().hex[:6]
        branch_name = f"feature/{slug}-{timestamp}"

        logger.info("Creating branch: %s", sanitize_for_log(branch_name))
        try:
            self._run_git_cmd(["checkout", "-b", branch_name])
            return branch_name
        except Exception as e:
            logger.warning("Failed to create branch: %s", sanitize_for_log(e))
            return ""

    def commit_changes(self, message: str) -> bool:
        """Stage and commit changes."""
        logger.info("Committing changes: %s", sanitize_for_log(message))
        try:
            self._run_git_cmd(["add", "."])
            output = self._run_git_cmd(["commit", "-m", message])
            return "nothing to commit" not in output
        except Exception as e:
            logger.warning("Failed to commit: %s", sanitize_for_log(e))
            return False

    def implement_feature(self, description: str, use_git: bool = False) -> dict[str, Any]:
        """
        Run the full implementation pipeline: Code -> Validate -> Test -> Document.

        Args:
            description: Feature description
            use_git: Whether to create a branch and commit changes
        """
        logger.info("Starting pipeline for: %s", sanitize_for_log(description))
        steps: list[StepResult] = []
        result: dict[str, Any] = {"steps": steps, "final_output": {}, "status": "success"}

        branch_name = ""
        if use_git:
            branch_name = self.create_feature_branch(description)
            if branch_name:
                steps.append({"step": "git_branch", "branch": branch_name, "status": "created"})

        # Step 1: Coding
        logger.info("Step 1: Coding")
        code_result = self.coding_agent.run(description)
        code = code_result.get("code", "")
        steps.append({"step": "coding", "output": code_result})

        if not code:
            result["status"] = "failed"
            result["error"] = "Coding agent failed to generate code"
            return result

        # Step 2: Validation
        logger.info("Step 2: Validation")
        violations = self.rule_engine.validate_code(code)
        validation_passed = len([v for v in violations if v.severity == "error"]) == 0

        steps.append(
            {
                "step": "validation",
                "passed": validation_passed,
                "violations": [v.dict() for v in violations],
            }
        )

        if not validation_passed:
            result["status"] = "failed"
            result["error"] = "Code validation failed"
            # In a real system, we would loop back to DebuggingAgent here
            return result

        # Step 3: Testing
        logger.info("Step 3: Testing")
        test_result = self.testing_agent.run("Create unit tests", context={"code": code})
        steps.append({"step": "testing", "output": test_result})

        # Step 4: Documentation
        logger.info("Step 4: Documentation")
        doc_result = self.docs_agent.run("Document this code", context={"code": code})
        steps.append({"step": "documentation", "output": doc_result})

        result["final_output"] = {
            "code": code,
            "tests": test_result.get("tests"),
            "docs": doc_result.get("documentation"),
        }

        # Step 5: Git Commit (if enabled)
        if use_git and branch_name and result["status"] == "success":
            # Note: In a real implementation, we would write the files to disk here before committing.
            # For this demo, we assume the user/agent handles file writing externally or we just commit what changed.
            commit_msg = f"feat(auto): implement {description[:50]}..."
            committed = self.commit_changes(commit_msg)
            if committed:
                steps.append({"step": "git_commit", "status": "committed", "message": commit_msg})

        return result
