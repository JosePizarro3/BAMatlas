# BAMatlas

BAMatlas is a staff directory for BAM expertise discovery. It is being built as a secure, low-friction Django application where users can register with their institutional email address, maintain a profile, and be discovered through structured expertise terms and search.

## Product Direction

- Authentication: local account signup with email verification now, institutional SSO later.
- Public data: name, family name, organisational entity, expertise, institutional email address.
- Private data: moderation state, audit-oriented metadata, and account security data.
- Search: in-app autocomplete and faceted filtering first, with a clean path to Elasticsearch in production later.
- Vocabulary control: users should prefer existing expertise terms, but they may add a new one when needed.

## Current Milestone

The foundation branch implements:

- Django 5.2 LTS scaffold
- custom user model from day one
- environment-aware settings
- secure production defaults
- local development instructions

The current authentication milestone adds:

- `@bam.de` account registration
- email verification
- moderation-ready activation
- sign in and sign out flows
- a basic authenticated account page

The current directory milestone adds:

- public profiles with structured expertise terms
- landing-page search and clickable expertise filters
- expertise autocomplete for search and profile editing
- a self-service profile editor for registered users
- public profile email addresses for direct contact
- controlled site locations limited to `UE`, `AH`, or `TTS`

The current admin-hardening milestone adds:

- profile moderation states and staff publication review
- audit events for approvals, deactivations, and directory moderation
- safer user deactivation instead of hard-delete workflows
- a staff-only moderation dashboard
- moderator access currently follows Django's `is_staff` flag

The current deploy-and-ops milestone adds:

- a production-oriented Docker image
- a local `docker-compose.yml` stack with PostgreSQL and Mailpit
- environment-driven deployment settings
- a `healthz` endpoint for health checks
- deployment notes and capacity estimates for BAM-scale rollouts

## Planned Milestones

1. `milestone/01-foundation`: scaffold, settings, custom user model, local setup.
2. `milestone/02-auth`: signup, login, email verification, BAM-domain restriction, moderation.
3. `milestone/03-directory`: profile model, expertise taxonomy, public directory, search, autocomplete.
4. `milestone/04-admin-hardening`: admin workflows, moderation UX, auditability, safer edit/delete rules.
5. `milestone/05-deploy-ops`: Dockerfile, deployment notes, Postgres and Elasticsearch integration, SSO roadmap.

## Local Development

### Recommended: Docker Compose

The recommended local workflow now uses Docker Compose with:

- Django app container
- PostgreSQL 16
- Mailpit for verification emails
- an optional Elasticsearch service profile for later experiments

Quick start:

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

4. Open:

   - app: `http://127.0.0.1:8000/`
   - email inbox: `http://127.0.0.1:8025/`

This setup runs migrations and `collectstatic` automatically when the `web` container starts.
Rebuild with `docker compose up --build` after code changes.

### Manual Local Development Without Docker

The project uses `uv` for dependency management.

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

Without Docker, email is sent to the console so verification links can be tested without external infrastructure.

During local testing, the intended flow is:

1. create an account with a `@bam.de` email address
2. verify the email
3. if admin approval is still required, approve the user through `/admin/` or `/directory/moderation/`
4. sign in through the public login page
5. complete the profile at `/directory/profile/edit/`
6. publish or review content through `/directory/moderation/` as staff when needed
7. explore the public directory at `/directory/`

## Deployment Notes

- Local database without Docker: SQLite by default.
- Local database with Docker Compose: PostgreSQL.
- Production database: PostgreSQL via `DATABASE_URL`.
- Search in development: Django ORM queries and lightweight autocomplete endpoints.
- Search in production: optional Elasticsearch integration once the app shape stabilises.
- Container health checks can target `/healthz/`.

See [docs/deployment.md](/home/jpizarro/work/BAMatlas/docs/deployment.md) for the deployment guide, Docker usage, and capacity estimates.
