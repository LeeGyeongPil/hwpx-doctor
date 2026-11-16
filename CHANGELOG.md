# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2026-11-16

### Added
- `hwpx-doctor check` with 13 rules (C000-C005, X001, M001-M003, R001-R003), text/JSON/SARIF output, exit codes 0/1/2, `--strict`, `--select`, `--ignore`, `--exit-zero`.
- `hwpx-doctor fix` with five byte-preserving safe repairs and an automatic re-check.
- `hwpx-doctor rules`, Python API (`check`, `fix`, `RULES`, ...), English and Korean output.
- pre-commit hook definition and example files.

### Fixed
- `check` on a folder without `.hwpx` files now exits 2 with a hint instead of passing silently.
- Deeply nested XML no longer raises `RecursionError`.
- `fix` error reports show the input path; multi-byte encoding declarations get a clear message instead of a misleading "not well-formed".
- CI workflow runs with read-only `contents` permission.
