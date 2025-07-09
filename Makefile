# Only for development
format:
	uv run ruff format -v .

lint:
	uv run ruff check --select I --fix .	

check:
	uv run pyright

unit-test:
	uv run pytest 

integration-test:
	uv run ./test/main.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	rm 

