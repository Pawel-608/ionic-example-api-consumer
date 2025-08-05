# ionic api example usage

you need to create `.env` file with:
```
IONIC_API_HOST="dev.api.ionic.trade"
IONIC_API_KEY='xxx'
```

and then run


```bash
poetry update
poetry run uvicorn demo.demo_server:app --reload --port 8001
```