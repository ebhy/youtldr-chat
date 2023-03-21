.PHONY: start
start:
	uvicorn app:app --reload --port 9000

.PHONY: format
format:
	black .
	isort .