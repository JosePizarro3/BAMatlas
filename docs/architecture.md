# Architecture Overview

## Core Choices

- Framework: Django 5.2 LTS
- Local database: SQLite
- Containerised local database: PostgreSQL via Docker Compose
- Production database: PostgreSQL
- Authentication now: local email-and-password accounts
- Authentication later: institutional SSO
- Search now: Django ORM queries and autocomplete endpoints
- Search later: optional Elasticsearch adapter

## Why This Shape

The first release needs strong security defaults without introducing operational complexity that would slow the project down. Django gives us:

- mature authentication and admin capabilities
- straightforward server-rendered pages
- good long-term maintainability
- easy deployment to conservative institutional environments

## Data Separation

The application will separate account data from public profile data:

- `accounts.User`: authentication, verification, moderation, staff rights
- `directory.Profile`: public person metadata
- `directory.ExpertiseTerm`: structured expertise vocabulary

That separation keeps private/security-sensitive concerns isolated from public directory data.

## Directory Design

The directory layer uses:

- `Profile`: one public-facing record per user
- `ExpertiseTerm`: reusable expertise vocabulary entries
- `ProfileExpertise`: explicit join table for profile-term relationships
 - `AuditEvent`: append-only operational history for approvals and moderation decisions

Public profile data now includes the institutional email address, because discoverability is only useful if colleagues can contact each other immediately from the directory.

`Profile.location` is intentionally constrained to the BAM site codes `UE`, `AH`, and `TTS` to avoid drifting free-text variants.

## Hardening Strategy

Milestone 4 introduces:

- staff review before first public profile publication
- pending-update tracking for edits to already-published profiles
- account deactivation instead of destructive deletion
- immutable-style audit records for user approvals and directory moderation

This keeps public data manageable without making the user flow heavy-handed.

Users can select existing expertise terms or type a new one. New terms are created immediately, but stored in a structured table so autocomplete and later governance remain possible.

## Elasticsearch Strategy

Docker Compose now leaves an explicit extension point for Elasticsearch in local environments. If you want to experiment later, there are three workable options:

1. Run without Elasticsearch and use the built-in Django search path. This is the recommended default during feature development.
2. Start the optional `elasticsearch` Compose profile for local experiments.
3. Use a shared remote development instance if BAM IT provides one.

For now, building the search layer behind a small abstraction will let us use the database locally and switch to Elasticsearch in production later without rewriting the UI.

## Deployment Shape

Milestone 5 adds:

- a single Docker image for local and production use
- a Compose stack with Django, PostgreSQL, Mailpit, and an optional Elasticsearch profile
- environment-variable driven configuration for database, hosts, email, and HTTPS settings
- a `healthz` endpoint for container or load-balancer health checks

This keeps the runtime model simple while remaining compatible with more conservative infrastructure teams.

## SSO Migration Plan

When BAM SSO access becomes available, the planned migration path is:

1. Keep `accounts.User` as the canonical local user table.
2. Add an authentication backend for the institutional identity provider.
3. Link external identities to existing local users by verified email address.
4. Disable local signup after SSO is stable, while preserving admin emergency access.
