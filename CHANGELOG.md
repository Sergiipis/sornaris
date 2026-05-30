# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Real provider adapters `OpenAIProvider` and `AnthropicProvider` (standard
  library only, API key read from the environment) plus a `build_provider`
  factory.
- CLI: `--provider {fake,openai,anthropic}`, `--scorer {exact,contains}`,
  `--cache PATH` (sqlite response cache), and `--models` to bisect the prompt
  **and** model axes together.
- `examples/` — runnable offline demos (`01_find_prompt_regression.py`,
  `02_multi_axis.py`) plus sample JSONL inputs for the CLI.
- Continuous integration (pytest matrix on Python 3.10–3.12, ruff lint +
  format check, build smoke test).

### Fixed
- Installed-package bug: `cli`, `search`, `multi`, and `runner` imported flat
  `bisect_*` module names with silent fallbacks; in an installed wheel those
  imports failed and the CLI bound a no-op `bisect_single_axis`, so it always
  reported `found: false`. Modules now import from the `sornaris` package, so
  the CLI and multi-axis search work after `pip install`.

### Changed
- Package formatted with `ruff format`; lint configured via `ruff`.

## [0.1.0]

- Initial engine: core models, scoring strategies, sqlite cache, offline
  providers, single-axis binary bisect, multi-axis orchestration, and an
  argparse CLI.
