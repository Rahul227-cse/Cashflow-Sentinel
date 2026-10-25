# Security policy

Use synthetic data only. Keep `.env`, Exasol passwords, remittance data, and
production customer records out of source control. Report a security concern
privately to the repository owner; do not publish credentials in an issue.

The prototype is local-only and must not expose Exasol directly to the public
internet. Rotate the Exasol password after any credential sharing event, then
update the local ignored `.env` file.
