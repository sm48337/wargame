export FLASK_APP=wargame

runserver:
	flask run

debug:
	FLASK_DEBUG=1 flask run

shell:
	flask shell
