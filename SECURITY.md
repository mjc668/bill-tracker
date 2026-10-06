# Security Policy

Bill Tracker is a self-hosted household application maintained by a small team.
We take security reports seriously and appreciate responsible disclosure.

## Reporting a vulnerability

**Please use GitHub's private vulnerability reporting:** repository → **Security**
→ **Advisories** → **Report a vulnerability**. This opens a private advisory
visible only to the maintainers.

Do not open a public issue, pull request, or discussion for a suspected
vulnerability. If you cannot use private advisories, contact a maintainer via
their GitHub profile and ask for a secure channel first.

Please include:

- the affected version or commit,
- steps to reproduce,
- the impact you believe this has,
- any suggested fix or mitigation.

## Scope

**In scope:** the Bill Tracker application in this repository — frontend, backend,
Docker images, compose files, backup/restore scripts, and the CI workflows.

**Out of scope:** vulnerabilities in third-party dependencies (report those
upstream; we track them with automated audits), misconfiguration of a
self-hosted deployment (exposed `.env`, missing TLS, firewall settings),
resource-exhaustion denial of service, social engineering, and physical attacks.

## Supported versions

Only the **latest published release** receives security fixes. Older releases
are not maintained; upgrade to the latest tag to stay supported.

## No bug bounty

This is a volunteer project. We cannot offer monetary rewards, but we are happy
to credit reporters in the advisory and release notes unless you prefer to stay
anonymous.

## What to expect

We aim to acknowledge reports within a few days, keep you updated on the
assessment, and coordinate disclosure timing with you before publishing an
advisory.
