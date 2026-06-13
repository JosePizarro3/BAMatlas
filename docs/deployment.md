# Deployment Guide

## Goals

- keep the deployment simple enough for institutional operations teams
- stay close to the local development shape
- leave clear extension points for PostgreSQL, SMTP, and later Elasticsearch or SSO

## Local Development With Docker Compose

This is now the recommended local workflow.

1. Copy the compose environment template:

   ```bash
   cp .env.compose.example .env.compose
   ```

2. Start the stack:

   ```bash
   docker compose up --build
   ```

3. Create the first admin user in another terminal:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

4. Open the app:

   - application: `http://127.0.0.1:8000/`
   - Mailpit inbox: `http://127.0.0.1:8025/`

5. Stop the stack:

   ```bash
   docker compose down
   ```

6. Remove persisted PostgreSQL data when you want a fresh database:

   ```bash
   docker compose down -v
   ```

Notes:

- the `web` container runs migrations and `collectstatic` automatically on startup
- the `db` service is PostgreSQL 16
- the `mailpit` service gives a browser inbox for verification emails
- the `elasticsearch` service is optional and starts only with `docker compose --profile search up`
- BAMatlas does not use Elasticsearch yet; the service is present so the compose file can grow naturally later
- rebuild with `docker compose up --build` when the application code changes

## Manual Production Deployment

The simplest production path is:

1. Provision PostgreSQL outside the container.
2. Put BAMatlas behind a TLS-terminating reverse proxy such as Nginx, Apache, or Traefik.
3. Run the Django app from the provided container image.

### Build The Image

```bash
docker build -t bamatlas:latest .
```

### Prepare Environment Variables

Copy `.env.example` to a private file such as `.env.production` and replace the placeholder values.

Required items:

- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL`
- SMTP settings if real email delivery is required

### Run The Container

```bash
docker run \
  --detach \
  --name bamatlas \
  --env-file .env.production \
  --publish 8000:8000 \
  bamatlas:latest
```

The entrypoint automatically runs:

- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`

### Reverse Proxy Expectations

The production settings assume:

- HTTPS is terminated before the Django container
- the proxy forwards `X-Forwarded-Proto: https`
- the public hostname is listed in `DJANGO_ALLOWED_HOSTS`
- the public HTTPS origin is listed in `DJANGO_CSRF_TRUSTED_ORIGINS`

### Health Checks

Use `GET /healthz/` for basic container and load-balancer health checks.

## Operational Recommendations

- keep one staff superuser for emergencies and use `is_staff` for normal moderators
- back up PostgreSQL daily, plus before each deployment
- keep `ACCOUNT_REQUIRE_ADMIN_APPROVAL=true` unless BAM decides to loosen onboarding later
- keep local signup available until institutional SSO is genuinely ready
- do not introduce Elasticsearch in production until the directory outgrows the current ORM search path

## Capacity Estimates

These estimates assume a small internal directory with server-rendered pages, PostgreSQL, no file uploads, and no Elasticsearch.

| Researchers | Expected peak concurrent users | App capacity | PostgreSQL capacity | Suggested disk | Notes |
| --- | --- | --- | --- | --- | --- |
| 100 | 5 | 1 vCPU, 1 GB RAM | 1 vCPU, 1 GB RAM | 10 GB | Fine on one small VM |
| 200 | 5-10 | 1 vCPU, 1.5 GB RAM | 1 vCPU, 1 GB RAM | 15 GB | Good baseline for pilot rollout |
| 500 | 10-20 | 2 vCPU, 2 GB RAM | 1-2 vCPU, 2 GB RAM | 25 GB | Prefer managed Postgres or separate DB host |
| 1000 | 20-40 | 2 vCPU, 3 GB RAM | 2 vCPU, 4 GB RAM | 40 GB | Comfortable production target without Elasticsearch |

Practical interpretation:

- for up to 200 researchers, one 2 vCPU and 4 GB RAM VM can host both Django and PostgreSQL comfortably
- for around 500 researchers, a 4 vCPU and 6 GB RAM setup is a safer target if app and database stay on the same machine
- for around 1000 researchers, prefer 4 vCPU and 8 GB RAM total, or split app and database into separate services
- the database itself will remain small; disk headroom is mostly for PostgreSQL growth, logs, backups, and operational comfort

## When Elasticsearch Becomes Worthwhile

Elasticsearch is probably unnecessary until one or more of these become true:

- the directory grows well beyond 1000 profiles
- search relevance requirements become much more advanced
- BAM wants typo tolerance, synonyms, or ranking rules beyond the current database approach
- search traffic becomes a noticeable part of total application latency

If Elasticsearch is introduced later, reserve roughly:

- 2 more vCPU
- 4 GB more RAM
- 20 GB more SSD storage

## SSO Follow-Up Plan

When BAM grants access to institutional SSO, the clean migration path is:

1. Add an SSO authentication backend while keeping `accounts.User` as the canonical user table.
2. Match incoming SSO identities to local users by verified institutional email.
3. Keep local superuser login as an emergency-only fallback.
4. Disable self-service password signup only after SSO is stable in production.
