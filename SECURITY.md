# Security Policy — AI Real Estate Assistant

**Last Updated:** 2026-11-06
**Version:** 5.1.6

## Reporting Security Issues

### Responsible Disclosure

If you discover a security vulnerability, please **disclose it privately**:

1. **Do not** create public GitHub issues for security vulnerabilities
2. **Do not** disclose vulnerability details publicly before a fix is available
3. **Do** send details to: **a.v.nesterovich@gmail.com** with subject `[SECURITY] AI Real Estate Assistant`
4. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)

### Response Timeline

| Severity | Description | Acknowledgment | Fix Target |
|----------|-------------|----------------|------------|
| P0 Critical | Data exposure, active exploitation | Within 24 hours | Within 48 hours |
| P1 High | Unauthorized access, service disruption | Within 48 hours | Within 72 hours |
| P2 Medium | Potential exposure, misconfiguration | Within 7 days | Within 2 weeks |
| P3 Low | Best practice deviation | Within 14 days | Next release |

### What to Expect

1. **Acknowledgment** - We will confirm receipt and assign a severity level
2. **Investigation** - We will investigate and may ask for additional details
3. **Fix** - We will develop and test a fix
4. **Disclosure** - We will coordinate public disclosure with you after the fix is deployed
5. **Credit** - Security researchers will be credited in advisories (if desired)

## Supported Versions

| Version | Supported |
|---------|-----------|
| 5.1.x | Yes |
| 5.0.x | Yes |
| 4.x and earlier | No |

## Security Features

For detailed information about the platform's security architecture, see [docs/security/SECURITY.md](docs/security/SECURITY.md).
The register of consciously accepted dependency risks lives in [docs/operations/security/accepted-risks.md](docs/operations/security/accepted-risks.md).

Key security measures include:

- API key authentication (required for all endpoints)
- JWT authentication for user-scoped features
- Input sanitization on all user-facing endpoints
- Rate limiting (per-client, Redis-backed in production)
- Security headers (CSP, HSTS, X-Frame-Options)
- Circuit breakers for LLM provider resilience
- Request ID correlation for incident tracing
- Pre-commit hooks (Gitleaks, Ruff, lint-staged)
- CI security scans (Bandit, Semgrep, Trivy, pip-audit)

## Security Best Practices for Contributors

- **Never commit secrets** - Use environment variables for all sensitive values
- **Use parameterized queries** - Never interpolate user input into SQL
- **Validate all inputs** - Use Pydantic v2 (Python) or Zod (TypeScript)
- **Run `make security`** - Before submitting PRs to catch issues early
- **Report, don't exploit** - If you find a vulnerability during development, report it privately

## Changelog

### 2026-03-29 - V5 Security Policy
- Extracted SECURITY.md to project root for GitHub security policy detection
- Added responsible disclosure process with response timeline
- Added supported versions section
- Linked to detailed security architecture document

### 2026-01-26 - V4 Security Enhancements
- Full security architecture documented in docs/security/SECURITY.md
