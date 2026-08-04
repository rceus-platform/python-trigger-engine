# Security Policy — Python Trigger Engine

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | ✅ Current release |

---

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please send a private report to the maintainers at **rhishikesh.chikhalkar@gmail.com** containing:

1. **Description** of the vulnerability and potential impact.
2. **Steps to reproduce** (or a proof-of-concept script).
3. **Suggested remediation** (if available).

### Response Expectations

- **Acknowledgement**: Within 48 hours.
- **Status Update & Assessment**: Within 5 business days.
- **Fix Release**: Communicated promptly once a patch is ready and validated.

---

## Security Best Practices

This project adheres to the following security guidelines:

- **Strict Secret Management**: No secrets, credentials, or API keys are stored in source control. Secrets are injected at runtime via environment variables or `/opt/secrets/` on production servers.
- **Base64 Encoded Deployment Secrets**: CI/CD deployment payloads are encrypted using GitHub Repository Secrets (`APP_SECRET_JSON_B64`).
- **Static Analysis & Linting**: Automated security checking via `ruff` linter rules (`S` ruleset) enforced in pre-commit and CI.
- **Automated Container & Dependency Scanning**: Dependencies are locked with SHA hashes in `uv.lock` to prevent supply-chain tampering.
