run:
	python3 main.py

test:
	git pull
	python3 main.py

ftest:
	git pull
	python3 main.py -f