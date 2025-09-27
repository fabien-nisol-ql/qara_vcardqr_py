# Python & venv
PYTHON ?= python3
PIP ?= $(VENV)/bin/pip
VENV ?= .venv

.PHONY: help install-os run venv install run_example
help:
	@echo "Targets:"
	@echo "  venv        - create virtualenv"
	@echo "  install     - install package (editable) + deps"
	@echo "  run         - run example QR build"
	@echo "  runyaml     - run example with YAML"
	@echo "  build       - build wheel + sdist"
	@echo "  clean       - remove build artifacts and venv"
	@echo "  qr          - generate a QR with CLI args (see README)"

$(VENV)/bin/activate: 
	$(PYTHON) -m venv $(VENV)
	@echo "Virtualenv created at $(VENV)"

venv: $(VENV)/bin/activate

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -e .
	@echo "Installed in editable mode."

install-os: build
	# Installs the wheel into your OS Python environment (pip3)
	pip3 install --upgrade dist/*.whl
	@echo "Installed system-wide via pip3."


run: install
	# Usage: make run ARGS="--yaml examples/contact.yaml --out out.png"
	$(VENV)/bin/vcardqr $(ARGS)

run_example: install
	$(VENV)/bin/vcardqr --yaml examples/contact.yaml

parse_example: run_example
	$(VENV)/bin/vcardqr --parse out/John.Doe-512px.png

build: install
	$(VENV)/bin/pip install --upgrade build
	$(VENV)/bin/python -m build

clean:
	rm -rf $(VENV) dist build *.egg-info .pytest_cache .mypy_cache
	find . -name '__pycache__' -type d -exec rm -rf {} +
	@echo "Cleaned."

qr: install
	# Example: make qr ARGS='--given-name John --family-name Doe --fn "John Doe" --out out.png'
	$(VENV)/bin/vcardqr $(ARGS)
