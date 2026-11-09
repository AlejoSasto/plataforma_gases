.PHONY: verify verify-fast verify-full real

real:
	python scripts/build_real_platform.py --confirm

verify:
	python scripts/verify.py

verify-fast:
	python scripts/verify.py --fast

verify-full:
	python scripts/verify.py --full
