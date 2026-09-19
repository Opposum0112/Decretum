# Security Policy

## Reporting a vulnerability

Please do not disclose an unpatched security vulnerability in a public issue.

Use GitHub's private security reporting mechanism for this repository when available. Include:

- affected version or commit
- affected file/component
- reproduction steps
- impact
- any suggested mitigation

Please allow maintainers reasonable time to investigate before public disclosure.

## Scope

Decretum is a compiler and resolver. It does not execute tools, provision environments, or own persistent research state.

Security reports should therefore distinguish:

- compiler/resolver vulnerabilities
- unsafe contract generation
- registry or validation bypasses
- dependency vulnerabilities
- documentation-only issues

Runtime vulnerabilities in an external harness or store should be reported to the project that owns that runtime.
