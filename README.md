## ionic trade api example usage

To run trade api demo:

add pk to `.env` file:

```
PRIVATE_KEY=base58_encoded_pk
```

then run

```bash
poetry update
poetry run python -m trader_api_demo
```

## ionic data api example usage

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