# Makefile for LLM Chat System
#Makefile (開発効率化用)

.PHONY: help install dev-install test lint clean docs run init health-check

# デフォルトターゲット
help:
	@echo "LLM Chat System - Available Commands:"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install      - Install production dependencies"
	@echo "  dev-install  - Install development dependencies"
	@echo "  init         - Initialize system"
	@echo ""
	@echo "Development Commands:"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage"
	@echo "  lint         - Run linting tools"
	@echo "  format       - Format code with Black"
	@echo "  clean        - Clean up generated files"
	@echo ""
	@echo "Documentation Commands:"
	@echo "  docs         - Build documentation"
	@echo "  docs-serve   - Serve documentation locally"
	@echo ""
	@echo "Runtime Commands:"
	@echo "  run          - Run the application"
	@echo "  run-gui      - Run with GUI interface"
	@echo "  health-check - Perform system health check"

# インストール関連
install:
	pip install -r requirements.txt

dev-install: install
	python scripts/dev.py setup

init:
	python scripts/init.py

# テスト関連
test:
	python scripts/dev.py test

test-cov:
	python scripts/dev.py test --coverage

# コード品質関連
lint:
	python scripts/dev.py lint

format:
	black src/ tests/ scripts/

# クリーンアップ
clean:
	python scripts/dev.py clean
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

# ドキュメント関連
docs:
	python scripts/dev.py docs

docs-serve: docs
	cd docs/_build && python -m http.server 8000

# 実行関連
run:
	python scripts/start.py

run-gui:
	python scripts/start.py --interface gui

run-debug:
	python scripts/start.py --debug

health-check:
	python scripts/start.py --health-check

# 開発用ショートカット
dev-setup: dev-install init
	@echo "Development environment ready!"

dev-test: lint test-cov
	@echo "Code quality checks completed!"

# CI/CD用
ci-test: install init test lint
	@echo "CI pipeline completed!"
