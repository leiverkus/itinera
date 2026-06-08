# Itinera – maintainer tasks. The QGIS plugin is the repo root itself;
# `make zip` packages it for QGIS "Install from ZIP". See scripts/package-plugin.sh.
.DEFAULT_GOAL := help

.PHONY: help zip test lint clean

help: ## Show this help
	@grep -hE '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed -E 's/:.*## / — /' | sort

zip: ## Build the QGIS plugin zip (itinera-<version>.zip) from HEAD
	scripts/package-plugin.sh

test: ## Run the GUI-free core test suite
	python -m pytest -q

lint: ## Run flake8 over core/ algorithms/ tests/
	python -m flake8 core/ algorithms/ tests/

clean: ## Remove built plugin zips
	rm -f itinera-*.zip
