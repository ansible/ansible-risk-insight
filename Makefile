
.PHONY: install
install:
	@echo installing ARI using pip
	pip install -e .


.PHONY: test
test:
	@echo testing codes with pytest
	pytest -s test


.PHONY: black
black:
	@echo linting codes with black \(auto-fix\)
	black ansible_risk_insight --line-length=150 --include='\.pyi?$$' --exclude="\.git|\.hg|\.mypy_cache|\.tox|\.venv|_build|buck-out|build|dist"


.PHONY: flake8
flake8:
	@echo linting codes with flake8
	flake8


.PHONY: lint
lint: black flake8