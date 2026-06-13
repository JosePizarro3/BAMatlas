# TODO

## Next Product Steps

- Integrate BAM institutional SSO once access to the identity provider is available.
- Decide whether local password signup should remain as an emergency fallback after SSO rollout.
- Review whether moderator assignment should move from `is_staff` to a dedicated Django group.
- Define a light governance process for cleaning or merging user-generated expertise terms in Django admin.

## Next Technical Steps

- Add a small set of role- and permission-focused tests for the moderation dashboard.
- Decide whether to add a dedicated rate-limiting layer in front of login, registration, and verification-resend endpoints.
- Evaluate whether autocomplete and search should move to Elasticsearch after real usage data is available.
- Add structured application logging if BAM IT wants central log shipping or SIEM integration.

## Operations Follow-Up

- Confirm production backup retention and restore testing expectations with BAM IT.
- Decide whether the Django admin should be IP-restricted, VPN-restricted, or reverse-proxy protected in production.
- Review HSTS `includeSubDomains` and `preload` only if BAM IT explicitly wants them for the chosen hostname.
