# BAMatlas

BAMatlas is a Django application for discovering BAM researchers by expertise. Users can register with their institutional email address, maintain a public expertise profile, and search the directory through structured expertise terms with autocomplete.

## Services And Stack

- Python 3.12+
- Django 5.2
- SQLite for local `uv` development
- PostgreSQL for Docker Compose and production-style setups
- Mailpit for local email testing with Docker Compose
- optional Elasticsearch service in Docker Compose for later experiments

## Minimal Requirements

- `uv` for local Python-based development, or
- Docker Engine with Docker Compose for container-based development
- a modern browser

## Local Development With Docker Compose

1. Copy the local environment file:

   ```bash
   cp .env.compose.example .env.compose
   ```

2. Start the stack:

   ```bash
   docker compose up --build
   ```

3. Create an admin account:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

4. Open the app at `http://127.0.0.1:8000/`

5. Open the email inbox at `http://127.0.0.1:8025/`

6. Stop the stack:

   ```bash
   docker compose down
   ```

7. Remove persisted database volumes when needed:

   ```bash
   docker compose down -v
   ```

The `web` container runs migrations and `collectstatic` on startup.

## Local Development With `uv`

1. Install dependencies:

   ```bash
   uv sync
   ```

2. Create the database and initial migration state:

   ```bash
   uv run python manage.py migrate
   ```

3. Create an admin account:

   ```bash
   uv run python manage.py createsuperuser
   ```

4. Start the local server:

   ```bash
   uv run python manage.py runserver
   ```

5. Open `http://127.0.0.1:8000/`

With the `uv` workflow, verification emails are printed to the console.

## Deployment

See [docs/deployment.md](/home/jpizarro/work/BAMatlas/docs/deployment.md) for Docker deployment, production configuration, and capacity guidance.
