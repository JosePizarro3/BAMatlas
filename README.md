# BAMatlas

BAMatlas is a staff directory for BAM expertise discovery. It is being built as a secure, low-friction Django application where users can register with their institutional email address, maintain a profile, and be discovered through structured expertise terms and search.

## Product Direction

- Authentication: local account signup with email verification now, institutional SSO later.
- Public data: name, family name, organisational entity, expertise.
- Private data: email address, moderation state, audit-oriented metadata.
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

## Planned Milestones

1. `milestone/01-foundation`: scaffold, settings, custom user model, local setup.
2. `milestone/02-auth`: signup, login, email verification, BAM-domain restriction, moderation.
3. `milestone/03-directory`: profile model, expertise taxonomy, public directory, search, autocomplete.
4. `milestone/04-admin-hardening`: admin workflows, moderation UX, auditability, safer edit/delete rules.
5. `milestone/05-deploy-ops`: Dockerfile, deployment notes, Postgres and Elasticsearch integration, SSO roadmap.

## Local Development

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

For local development, email is sent to the console so verification links can be tested without external infrastructure. During milestone 2, the intended local flow is:

1. create an account with a `@bam.de` email address
2. copy the verification link from the terminal output
3. open the link in the browser
4. if admin approval is still required, approve the user through `/admin/`
5. sign in through the public login page

## Architecture Notes

- Local database: SQLite by default.
- Production database: PostgreSQL via `DATABASE_URL`.
- Search in development: Django ORM queries and lightweight autocomplete endpoints.
- Search in production: optional Elasticsearch integration once the app shape stabilises.

Docker is not required for development. It is still reasonable to provide a `Dockerfile` later for deployment and reproducibility.
