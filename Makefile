.PHONY: install test unit integration labs e2e cov trace clean

install:
	uv venv
	uv pip install -e ".[dev,services,models]"

# CI-equivalent: unit + integration (e2e excluded by default addopts).
test: unit integration

unit:
	uv run pytest tests/ -m unit -q

integration:
	uv run pytest tests/ -m integration -q

# Run every challenge's reference solution suite (should be all green).
labs:
	@for dir in challenges/*/; do \
		echo "=== $$dir ==="; \
		uv run pytest "$$dir/tests" -q \
			-m "functional or exploit or invariant or adversarial" \
			--challenge="$$dir" --solution || exit 1; \
	done

# E2E over real HTTP services — MANUAL ONLY, never in CI.
e2e:
	uv run pytest tests/e2e -m e2e -q

cov:
	uv run pytest tests/ -m "unit or integration" \
		--cov=dvah --cov-report=term-missing --cov-fail-under=80 -q

clean:
	rm -rf .venv .pytest_cache .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
