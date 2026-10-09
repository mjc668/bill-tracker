# Security Policy

Platybill is a self-hosted household application maintained by a small team.
We take security reports seriously and appreciate responsible disclosure.

## Reporting a vulnerability

**Please use GitHub's private vulnerability reporting:** repository → **Security**
→ **Advisories** → **Report a vulnerability**. This opens a private advisory
visible only to the maintainers.

Do not open a public issue, pull request, or discussion for a suspected
vulnerability. If you cannot use private advisories, contact a maintainer via
their GitHub profile and ask for a secure channel first.

Please include:

- the affected image tag (`sha-<7>`, `main`, or `latest`) or commit,
- steps to reproduce,
- the impact you believe this has,
- any suggested fix or mitigation.

## Scope

**In scope:** the Platybill application in this repository — frontend, backend,
the all-in-one Docker image, compose files, backup/restore scripts, and the CI
workflows.

**Out of scope:** vulnerabilities in third-party dependencies (report those
upstream; we track them with automated audits), misconfiguration of a
self-hosted deployment (exposed `.env`, missing TLS, firewall settings),
resource-exhaustion denial of service, social engineering, and physical attacks.

## Supported versions

Platybill has no versioned releases: every green commit on `main` is published
as an immutable `sha-<7>` image tag, and `main`/`latest` roll forward to the
newest build. Only the **newest build** receives security fixes — upgrade to the
latest tag (or re-pull the tag you follow) to stay supported.

## No bug bounty

This is a volunteer project. We cannot offer monetary rewards, but we are happy
to credit reporters in the advisory unless you prefer to stay anonymous.

## What to expect

We aim to acknowledge reports within a few days, keep you updated on the
assessment, and coordinate disclosure timing with you before publishing an
advisory.
