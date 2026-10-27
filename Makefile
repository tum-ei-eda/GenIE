all: dist
.PHONY: dist
dist: venv/manifest.txt
	./venv/bin/poetry build

.PHONY: mount
mount:
	@echo "make mount is not needed in GenIE. You may simply call 'genie --dockerized'."

.PHONY: pull-genie
pull-genie:
	@echo "GenIE will automatically pull Docker containers when it needs them."

.PHONY: genie
genie:
	@echo "make genie is deprecated. Please use make docker-image."
	@echo "----"
	@$(MAKE) docker-image

.PHONY: docker-image
docker-image:
	cat $(shell nix build --no-link --print-out-paths .#genie-docker -L --verbose) | docker load

.PHONY: docs
DOCS_PYTHON ?= python3
docs:
	$(DOCS_PYTHON) scripts/build_docs.py

.PHONY: host-docs
host-docs:
	$(DOCS_PYTHON) -m http.server --bind 127.0.0.1 --directory ./docs/_build/html

.PHONY: watch-docs
watch-docs:
	nodemon -w docs -w genie -w scripts -e md,rst,py,txt \
		-i 'docs/_build/**' -x '$(MAKE) docs && $(MAKE) host-docs'

.PHONY: lint
lint:
	black --check .
	flake8 .
	mypy --check-untyped-defs .

.PHONY: coverage-infrastructure
coverage-infrastructure:
	python3 -m pytest -n auto\
		--cov=genie --cov-config=.coveragerc --cov-report html:htmlcov_infra --cov-report term

.PHONY: coverage-steps
coverage-steps:
	python3 -m pytest -n auto\
		--cov=genie.steps --cov-config=.coveragerc-steps --cov-report html:htmlcov_steps --cov-report term\
		--step-rx "." -k test_all_steps

.PHONY: check-license
check-license: venv/manifest.txt
	./venv/bin/python3 -m pip freeze > ./requirements.frz.txt
	docker run -v `pwd`:/volume \
		-it --rm pilosus/pip-license-checker \
		java -jar app.jar \
		--requirements '/volume/requirements.frz.txt'

venv: venv/manifest.txt
venv/manifest.txt: ./pyproject.toml
	rm -rf venv
	python3 -m venv ./venv
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade pip
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade wheel poetry poetry-plugin-export
	PYTHONPATH= ./venv/bin/poetry export --with dev --without-hashes --format=requirements.txt --output=requirements_tmp.txt
	PYTHONPATH= ./venv/bin/python3 -m pip install --upgrade -r requirements_tmp.txt
	PYTHONPATH= ./venv/bin/python3 -m pip freeze > $@
	@echo ">> Venv prepared."

.PHONY: veryclean
veryclean: clean
veryclean:
	rm -rf venv/

.PHONY: clean
clean:
	rm -rf build/
	rm -rf logs/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf designs/*/runs
	rm -rf test_data/designs/*/runs
	rm -rf test/designs/*/runs
