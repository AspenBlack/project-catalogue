# Project Catalogue Makefile
# Works on Windows (with make installed), macOS, and Linux

.PHONY: help init scan build-docs serve all clean

SCANNER_DIR := scanner
MKDOCS_DIR := mkdocs

help:
	@echo "Project Catalogue - Available Commands:"
	@echo ""
	@echo "  make init         - First-time setup (configure scan paths)"
	@echo "  make scan         - Discover projects and generate projects.json"
	@echo "  make build-docs   - Build MkDocs documentation"
	@echo "  make serve        - Serve documentation locally (http://localhost:8000)"
	@echo "  make all          - scan + build-docs + serve"
	@echo "  make clean        - Remove generated files"
	@echo ""

init:
	cd $(SCANNER_DIR) && python cli.py init

scan:
	cd $(SCANNER_DIR) && python cli.py scan

list:
	cd $(SCANNER_DIR) && python cli.py list

build-docs: scan
	cd $(MKDOCS_DIR) && python generate_pages.py
	@echo ""
	@echo "Documentation built successfully."
	@echo "View it with: make serve"

serve:
	cd $(MKDOCS_DIR) && mkdocs serve

all: scan build-docs serve

clean:
	rm -rf $(MKDOCS_DIR)/site/
	rm -f projects.json
	find $(MKDOCS_DIR)/docs/projects -name "*.md" ! -name "index.md" -delete
	@echo "Cleaned up generated files."

.DEFAULT_GOAL := help
