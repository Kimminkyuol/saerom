.PHONY: test check format examples install vsix install-extension clean

CODE ?= $(shell command -v code 2>/dev/null || \
	echo "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")
VSIX = $(wildcard editors/vscode/saerom-*.vsix)

test:
	python3 -m unittest discover -s tests -t . -v

check:
	python3 -m saerom --check saerom/stdlib/*.sr examples/*.sr

format:
	python3 -m saerom --format saerom/stdlib/*.sr examples/*.sr

examples:
	@for f in examples/*.sr; do \
		echo "── $$f"; python3 -m saerom "$$f" </dev/null; \
	done

install:
	python3 -m pip install -e .

vsix:
	cd editors/vscode && npm install && npx --yes @vscode/vsce package

install-extension: vsix
	"$(CODE)" --install-extension $$(ls editors/vscode/saerom-*.vsix | tail -1) --force

clean:
	rm -rf build dist *.egg-info editors/vscode/saerom-*.vsix
	find . -name __pycache__ -type d -exec rm -rf {} +
