.PHONY: build bump lint test clean

build:
	@echo "▶ Building ktui binary via PyInstaller"
	hatch run build-bin
	@echo "▶ Staging binary into npm package"
	@python3 scripts/stage_binary.py

bump:
	@if [ -z "$(v)" ]; then echo "Error: specify v=<version>, e.g. make bump v=0.1.4"; exit 1; fi
	hatch version $(v)
	cd npm-package && npm version $(v) --no-git-tag-version
	@echo "✓ Version bumped to $(v) in pyproject.toml and package.json"

lint:
	hatch run ruff check .
	hatch run mypy src/ktui --strict || true

test:
	hatch run pytest -q --cov=ktui --cov-report=term-missing

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
