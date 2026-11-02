.PHONY: verify verify-fast verify-full

verify:
	python scripts/verify.py

verify-fast:
	python scripts/verify.py --fast

verify-full:
	python scripts/verify.py --full
