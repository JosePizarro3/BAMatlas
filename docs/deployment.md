# Deployment Guide

This guide is written for BAM IT or any operator deploying BAMatlas in a conservative institutional environment.

## What BAMatlas Needs

- Python 3.12 inside the application image
- PostgreSQL for persistent application data
- SMTP for real verification email delivery
- a reverse proxy or load balancer that terminates HTTPS
- Docker for the provided image-based deployment path

BAMatlas does not currently require Redis, Celery, file storage, or Elasticsearch.

## Recommended Local Workflow

Use Docker Compose for local validation because it matches the production shape most closely.

1. Copy the compose environment file:

   ```bash
   cp .env.compose.example .env.compose
   ```

2. Start the stack:

   ```bash
   docker compose up --build
   ```

3. Create the first admin user:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

4. Open the local services:

   - application: `http://127.0.0.1:8000/`
   - Mailpit inbox: `http://127.0.0.1:8025/`

5. Stop the stack:

   ```bash
   docker compose down
   ```

6. Remove persisted PostgreSQL data for a clean reset when needed:

   ```bash
   docker compose down -v
   ```

Notes:

- the `web` container runs `migrate` and `collectstatic` on startup
- the `db` service is PostgreSQL 16
- the `mailpit` service is only for local testing
- the `elasticsearch` Compose profile is optional and not used by the application today

## Production Deployment Pattern

The simplest production deployment is:

1. Provision PostgreSQL outside the application container.
2. Put BAMatlas behind an HTTPS reverse proxy such as Nginx, Apache, or Traefik.
3. Run the provided Django container image.
4. Restrict Django admin access according to BAM IT policy.

## Build The Image

```bash
docker build -t bamatlas:latest .
```

## Prepare The Environment

Copy `.env.example` to a private file such as `.env.production` and replace every placeholder value.

Required settings:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- SMTP settings for real email delivery

Recommended settings review:

- keep `ACCOUNT_REQUIRE_ADMIN_APPROVAL=true`
- keep `DJANGO_SECURE_SSL_REDIRECT=true`
- review HSTS flags with BAM IT before enabling `includeSubDomains` or `preload`

## Run The Container

```bash
docker run \
  --detach \
  --name bamatlas \
  --env-file .env.production \
  --publish 8000:8000 \
  bamatlas:latest
```

Container startup automatically runs:

- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`

## Reverse Proxy Expectations

Production settings assume:

- HTTPS is terminated before the Django container
- the proxy forwards `X-Forwarded-Proto: https`
- the public hostname is listed in `DJANGO_ALLOWED_HOSTS`
- the public HTTPS origin is listed in `DJANGO_CSRF_TRUSTED_ORIGINS`

## Security Notes

Current hardening in the application includes:

- Django CSRF protection and server-rendered templates with escaping enabled
- password hashing with Argon2 support
- email verification before login
- optional admin approval before first activation
- non-destructive deactivation instead of user deletion
- audit events for approvals and moderation actions
- public expertise autocomplete limited to expertise terms already visible in the public directory

Operational recommendations:

- keep one emergency superuser and use `is_staff` for normal moderators
- place the Django admin behind VPN, reverse-proxy restriction, or an IP allowlist if BAM policy allows it
- back up PostgreSQL daily and before deployments
- rotate the Django secret key only as part of a planned maintenance event
- do not expose PostgreSQL directly to the public internet

## Health Checks

Use `GET /healthz/` for container and load-balancer health checks.

## Validation Before Deployment

Run these checks before promoting changes:

```bash
uv sync --dev
uv run ruff check .
uv run pre-commit run --all-files
uv run pytest
uv run python manage.py check
```

## Capacity Estimates

These estimates assume a small internal directory with server-rendered pages, PostgreSQL, no file uploads, and no Elasticsearch.

| Researchers | Expected peak concurrent users | App capacity | PostgreSQL capacity | Suggested disk | Notes |
| --- | --- | --- | --- | --- | --- |
| 100 | 5 | 1 vCPU, 1 GB RAM | 1 vCPU, 1 GB RAM | 10 GB | Fine on one small VM |
| 200 | 5-10 | 1 vCPU, 1.5 GB RAM | 1 vCPU, 1 GB RAM | 15 GB | Good baseline for pilot rollout |
| 500 | 10-20 | 2 vCPU, 2 GB RAM | 1-2 vCPU, 2 GB RAM | 25 GB | Prefer managed PostgreSQL or a separate DB host |
| 1000 | 20-40 | 2 vCPU, 3 GB RAM | 2 vCPU, 4 GB RAM | 40 GB | Comfortable production target without Elasticsearch |

Practical interpretation:

- up to 200 researchers: one 2 vCPU and 4 GB RAM VM can host both app and database comfortably
- around 500 researchers: 4 vCPU and 6 GB RAM is a safer target if app and DB share one machine
- around 1000 researchers: prefer 4 vCPU and 8 GB RAM total, or split app and DB into separate services

## FAQ And Troubleshooting

### Why are new users unable to log in immediately after registration?

They must verify their email first. If `ACCOUNT_REQUIRE_ADMIN_APPROVAL=true`, a moderator must also approve the account before first login.

### Why does the directory autocomplete not show a term that a user just entered?

Autocomplete only exposes expertise terms attached to publicly visible profiles. This avoids leaking terms from draft, private, or unpublished profiles.

### The site loads, but verification emails are not arriving

Check:

- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`
- `EMAIL_USE_TLS` and `EMAIL_USE_SSL`
- whether the SMTP server accepts the `DEFAULT_FROM_EMAIL` address
- container logs for SMTP connection errors

### Static files are missing in production

Check:

- startup logs for `collectstatic`
- that the reverse proxy serves `/static/` correctly if it is terminating requests itself
- that `DJANGO_SETTINGS_MODULE=config.settings.production` is actually set

### CSRF errors appear after putting BAMatlas behind a proxy

Check:

- `DJANGO_CSRF_TRUSTED_ORIGINS` includes the full public HTTPS origin
- the proxy forwards `X-Forwarded-Proto: https`
- the hostname is present in `DJANGO_ALLOWED_HOSTS`

### BAM IT wants stricter transport security

Start with HTTPS redirect and secure cookies, then review:

- `DJANGO_SECURE_HSTS_SECONDS`
- `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `DJANGO_SECURE_HSTS_PRELOAD`

Do not enable `includeSubDomains` or `preload` unless BAM IT has explicitly reviewed the impact for the deployed hostname.

## SSO Follow-Up Plan

When BAM grants access to institutional SSO, the migration path is:

1. Add an SSO authentication backend while keeping `accounts.User` as the canonical user table.
2. Match incoming SSO identities to local users by verified institutional email.
3. Keep local superuser login as an emergency fallback.
4. Disable self-service password signup only after SSO is stable in production.
