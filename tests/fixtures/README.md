# Test Fixtures

This directory contains integration test fixtures utilized by Stitch QA end-to-end automated tests:

| Fixture | Target Scenario | Expected Gate Verdict |
| :--- | :--- | :--- |
| **`test-project`** | Python application with a failing regression test (demo project) | `BLOCK_RELEASE` (Exit 1) |
| **`test-docker-pytest-pass`** | Containerized Python application with clean passing test suite | `ALLOW_RELEASE` (Exit 0) |
| **`test-project-python-source-only`** | Python repository without test suite to verify test completeness checks | `QA_INCOMPLETE` (Exit 1) |
| **`test-project-php-unsupported`** | Unsupported language project to verify graceful scanner discovery | Exit 0 (Non-blocking skip) |
