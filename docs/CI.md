# Continuous integration

Two independent GitHub Actions workflows run on pushes, pull requests, and manual dispatch.
Both use Python 3.10 (the declared minimum), 3.12, and 3.14 on Ubuntu 24.04.

- **CI** (`.github/workflows/ci.yml`) installs the package from `pyproject.toml`, checks
  dependency consistency and Python syntax, runs all configuration tests, smoke-tests
  installed CLI entry points, and builds/checks the wheel and source distribution.
- **Migration tests** (`.github/workflows/migration-tests.yml`) runs every test under
  `test/steps` and `test/integration`. It also runs nightly. It checks out the audited
  prototype and toolkit revisions, sets `GENIE_DEMO_SRC` / `GENIE_TOOLKIT_SRC`, and
  installs `zstd` so reference integration and artifact tests execute. The job rejects
  skipped or empty test results. JUnit reports are uploaded even when tests fail.

New tests in those directories are discovered automatically. Configuration tests,
including CLI overrides and preprocessor regressions, run in the CI workflow.
Neither workflow needs service credentials, hardware licenses, a PDK, or the local
Docker installation used for manual workload validation. HTTP/service transport
fixtures and real toolkit utility tests execute in hosted CI; full compiler,
simulator, HLS and synthesis builds remain external validation tasks.

The reference revisions are pinned to the versions audited in `PROGRESS.md`:

| Repository | Revision |
| --- | --- |
| `PhilippvK/isaac-demo` | `fb3acb1ddcb3af2903837cb45ddba19b289ed5a7` |
| `tum-ei-eda/isaac-toolkit` | `b288f41d390316650003653080bdfb3d2cad270a` |

Update these pins deliberately when updating the audited reference behavior.
The package's runtime dependencies continue to come from `pyproject.toml`.

## Audit of the previous workflow (2026-10-22)

The previous `ci.yml` was inherited from OpenLane and was not executable for the
current GenIE checkout:

- Python 3.8/3.9 jobs contradicted `requires-python >=3.10`.
- Nix jobs referenced absent `flake.nix` / flake outputs.
- Design jobs referenced absent `test/designs` and `test/steps/all` submodules.
- pytest received the unregistered `--pdk-root` option.
- PDK setup used `steps.set-rev.outputs.opdks_rev` without a `set-rev` step.
- Docker smoke/design commands passed obsolete PDK/smoke-test CLI options.
- Metrics publication and image/PyPI release jobs depended on those obsolete builds.

Those jobs have been replaced by the package/configuration workflow above.
Automatic image/metrics/PyPI publication is no longer scheduled by this workflow;
it needs a separately designed GenIE release pipeline with valid build inputs.
The old composite actions and matrix helper files remain as historical sources
but are not referenced by the active workflows. The replacement CI does not invoke
`make lint`: that legacy target combines repository-wide Black/flake8/mypy checks;
format/type cleanup is separate from the migration regression suite.

Local validation used a fresh Python 3.10 virtual environment: installed-package
checks, 138 migration tests with zero skips, four configuration tests, CLI smoke
checks, wheel/sdist build and `twine check` all passed. `actionlint` 1.7.12 accepted
both workflow files. Other matrix interpreters and hosted-runner execution are
verified by GitHub once these changes are pushed; local results do not establish
a green hosted workflow.
