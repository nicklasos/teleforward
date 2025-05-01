.PHONY: install run test test-cov

install:
	pip install -r requirements.txt

run:
	. venv/bin/activate && nohup python src/main.py > bot.log 2>&1 & echo $$! > bot.pid

dev:
	python src/main.py

test:
	pytest tests/

test-cov:
	pytest --cov=src tests/ 