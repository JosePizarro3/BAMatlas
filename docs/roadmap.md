# Incremental Roadmap

## Milestone 1: Foundation

Objective: create a production-oriented Django base that is easy to run locally and safe to extend.

Includes:

- dependency management with `uv`
- settings split for local and production
- custom user model
- secure defaults and admin access

Exit criteria:

- the app starts locally
- migrations apply cleanly
- an admin user can be created

## Milestone 2: Authentication

Objective: allow BAM users to register with email verification and controlled activation.

Includes:

- email/password signup
- `@bam.de` domain restriction
- verification email flow
- optional admin moderation before full activation
- public login and logout pages
- account status page for confirmed users

## Milestone 3: Directory

Objective: make expertise discoverable through structured profile data and a public search experience.

Includes:

- profile model
- expertise term model
- searchable directory
- autocomplete and clickable filters

## Milestone 4: Admin Hardening

Objective: make the system safer and easier to operate.

Includes:

- admin moderation workflows
- safer edit and deletion controls
- stronger permission boundaries
- audit-friendly timestamps and status fields

## Milestone 5: Deployment and SSO

Objective: prepare the app for institutional deployment and future authentication integration.

Includes:

- Dockerfile
- production deployment notes
- PostgreSQL guidance
- Elasticsearch integration plan
- SSO implementation plan
