# Frontend Console

This folder contains a lightweight static frontend for manual interaction with the API.

## Features

- Register and login
- Upload audio files
- Check job status and results
- Poll job status automatically
- Check health and inspect a metrics sample

## Run with Docker Compose

From `srcs/`:

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- API: http://localhost:8000

## Run frontend only (without Docker)

From this folder:

```bash
python3 -m http.server 5173
```

If running this way, ensure the API has CORS enabled for `http://localhost:5173` (already configured in the API defaults).
