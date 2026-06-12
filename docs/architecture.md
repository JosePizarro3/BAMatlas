# Architecture Overview

## Core Choices

- Framework: Django 5.2 LTS
- Local database: SQLite
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
- future `directory.Profile`: public person metadata
- future `directory.ExpertiseTerm`: structured expertise vocabulary

That separation keeps private/security-sensitive concerns isolated from public directory data.

## Elasticsearch Strategy

Docker is not required for Elasticsearch in development. If you want to experiment locally later, there are three workable options:

1. Run without Elasticsearch and use the built-in Django search path. This is the recommended default during feature development.
2. Install Elasticsearch separately on a machine where you have the capacity to manage services manually.
3. Use a shared remote development instance if BAM IT provides one.

For now, building the search layer behind a small abstraction will let us use the database locally and switch to Elasticsearch in production later without rewriting the UI.

## SSO Migration Plan

When BAM SSO access becomes available, the planned migration path is:

1. Keep `accounts.User` as the canonical local user table.
2. Add an authentication backend for the institutional identity provider.
3. Link external identities to existing local users by verified email address.
4. Disable local signup after SSO is stable, while preserving admin emergency access.
