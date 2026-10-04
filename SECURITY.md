# Security policy

## Reporting a vulnerability

Please don't open a public issue for a security problem. Report it privately with
[GitHub private vulnerability reporting](https://github.com/dioxtra/SniffCraft-Wireshark/security/advisories/new)
(*Security* tab > *Report a vulnerability*), with the steps to reproduce it and the version you used.

Only the [latest release](https://github.com/dioxtra/SniffCraft-Wireshark/releases/tag/latest) gets fixes.

## Scope

In scope, for example:
- the proxy accepting connections it shouldn't, or exposing the logged in Microsoft account
- the credentials cache (``botcraft_cached_credentials.json``) leaking outside of the extcap folder
- crashes or code execution caused by packets from a malicious server or client, in SniffCraft or in the Wireshark dissectors
- the release workflow or the published files (checksums, attestations)

Problems in the code shared with [SniffCraft](https://github.com/adepierre/SniffCraft) and
[Botcraft](https://github.com/adepierre/Botcraft) also affect those projects, they will be reported there too.

The [Security and privacy](README.md#security-and-privacy) section of the README explains what the captures and the
credentials cache contain.
