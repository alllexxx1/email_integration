run:
	python manage.py runserver

daphne-start:
	daphne -p 8001 email_integration.asgi:application

redis-start:
	redis-server

redis-check:
	redis-cli ping

redis-kill:
	sudo service redis-server stop

lint:
	flake8