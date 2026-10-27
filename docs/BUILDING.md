# Building and publishing documentation

GenIE uses Sphinx, MyST Markdown, and Furo. Guides remain in `docs/*.md`;
the build generates references from the installed package's flow and step
registries, configuration variables, CLI help, and core Python docstrings.
No EDA tools, services, PDKs, or prototype checkouts are needed to build the site.

## Build locally

Use Python 3.12, as in the documentation CI job:

```sh
python3.12 -m venv /tmp/genie-docs-venv
source /tmp/genie-docs-venv/bin/activate
python -m pip install . -r docs/requirements.txt
make docs
make host-docs
```

Open <http://localhost:8000>. `make docs` fails on Sphinx warnings, including
unresolved document references. The output is `docs/_build/html/` and is ignored
by Git. With `nodemon` installed, `make watch-docs` rebuilds and restarts the
preview server after edits to guides, Python code, or build scripts.

For an optional network-dependent external link audit:

```sh
python scripts/build_docs.py --builder linkcheck --output-dir docs/_build/linkcheck
```

The build script stages sources in a temporary directory that mirrors the
repository, preserving links to `../PROGRESS.md` and downloadable `../cfg/` files.
It does not modify the handwritten guides. Generated reference pages are build
outputs: update Python registrations, variable descriptions, or CLI definitions
to change them. Add handwritten pages to the toctrees in `docs/index.md`.

## GitHub Actions

`.github/workflows/docs.yml` builds on pushes to `main` and `refactor2`, on pull
requests, and on manual dispatch. Every build uploads a `documentation-html`
artifact that can be downloaded, extracted, and served locally for review.
Only a successful build on `main` publishes to GitHub Pages. Pull requests and
`refactor2` never deploy. Publishing uses GitHub's Pages artifact and OIDC actions;
no personal access token or generated `gh-pages` branch is needed.

Before the first deployment, a repository administrator must select
**Settings → Pages → Build and deployment → Source: GitHub Actions**. In
**Settings → Environments → github-pages**, restrict deployments to `main`.
Merge the documentation setup into `main` (or run the workflow there) to publish.
The expected URL is <https://tum-ei-eda.github.io/GenIE/>.

## Design and upstream precedent

OpenLane 2 uses [Sphinx with MyST and Furo](https://github.com/chipfoundry/openlane2/blob/main/docs/source/conf.py),
custom generators for flow/step/configuration references, and autodoc for Python
APIs. Its [Read the Docs configuration](https://github.com/chipfoundry/openlane2/blob/main/.readthedocs.yml)
installs the package and documentation requirements, then builds HTML. GenIE
uses the same documentation stack, with
[GitHub Pages Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
for hosting. Versioned releases can be added later if multiple supported GenIE
versions need separate documentation sites.
