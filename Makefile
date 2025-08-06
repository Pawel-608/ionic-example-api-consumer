sync:
	poetry update

run-demo:
	poetry run gunicorn -w 1 -k uvicorn.workers.UvicornWorker demo.demo_server:app --bind 0.0.0.0:80
