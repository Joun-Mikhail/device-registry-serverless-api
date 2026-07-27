# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Because the service has not been released or deployed to a public environment,
everything to date sits under Unreleased.

## [Unreleased]

### Added
- `CI` workflow running unit tests with an 80% coverage gate and `ruff` lint on
  every push and pull request (Python 3.12).
- Dependabot configuration for weekly `pip` updates.
- MIT licence.
- Mermaid architecture, request-flow, and CI/CD pipeline diagrams, rendered
  inline by GitHub.
- Regression tests covering `pathParameters` arriving as `null`.
- Boundary tests for the device name length limit.
- Contributor guide, changelog, pull request and issue templates, and CODEOWNERS.

### Fixed
- `GET`, `PATCH`, and `DELETE` raised `AttributeError` when API Gateway sent
  `"pathParameters": null` instead of omitting the key. The exception escaped the
  handler's boundary `except`, so callers received a raw 502 rather than the
  documented error envelope. All three now return a 400.
- The name length limit was measured against the raw request value while handlers
  persisted the stripped value, so a name of exactly 100 characters submitted with
  surrounding whitespace was rejected despite fitting once trimmed.
- Lint violations surfaced by `ruff` 0.16's expanded default rule set.

### Changed
- Extracted the `DeviceRepository` singleton accessor, which had been duplicated
  verbatim across all five handlers, into `repositories.device_repository`.
- Replaced the repeated `"active"` literal with a `DEFAULT_STATUS` constant.
- Replaced repository-wide `ruff` ignores for `BLE001` and `TRY004` with per-line
  `noqa` directives and an explanatory comment at each of the six sites, so the
  rules stay active for new code.
- Reworded the README's observability and security sections to describe what
  `template.yaml` provisions rather than asserting a running deployment, and
  corrected the repository structure block and test counts to match reality.
- Raised dev dependency floors to the versions CI already installs.

### Security
- Disabled Vercel git deployments. The integration failed on every commit because
  the repository has no Python web entrypoint by design.
