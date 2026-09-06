## Description

Please include a summary of the change and which issue is fixed. Please also include relevant motivation and context.

Fixes # (issue)

## Commit hygiene

This repo uses **Squash and merge**. The squash commit is generated from this PR,
so:

- **PR title** MUST be a valid [Conventional Commit](https://www.conventionalcommits.org/)
  — it becomes the squashed commit subject (`feat:`, `fix:`, `docs:`, `chore:`,
  `refactor:`, `perf:`, `test:`, `ci:`...).
- **One PR = one concern.** Keep the diff focused; split unrelated work into
  separate PRs so each squashes to one meaningful commit on the target branch.
- Fill the **Description** above with care — it becomes the squashed commit body.
- Draft/WIP commits inside the PR are fine; they get squashed away on merge.

> Target branch: `dev` for feature work. `main` is protected (releases only).
> Direct pushes to `dev` are allowed but bypass squash — prefer a PR when you
> want a clean, traceable commit.

## Type of change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## CE Compliance

- [ ] No Pro/Enterprise-only features introduced in CE code paths
- [ ] New connectors added to correct allowlist section (`mcp/config/mcp_allowlist.yaml`)
- [ ] Edition gating respected (CE features freely accessible, Pro/Enterprise gated)

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] License headers added to new files (`SPDX-License-Identifier: MIT`)
- [ ] No secrets, API keys, or credentials in the diff

## DCO

- [ ] I certify that I have the right to submit this contribution under the project's license (see CONTRIBUTING.md DCO section)

## Testing

Describe how you tested the changes:

-
-

## Screenshots (if applicable)

Add screenshots to help explain visual changes.
