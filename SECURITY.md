# Security

LCA Wrench listens on 127.0.0.1 only and is meant for one local user. It has no authentication. Do not expose it to a
network (no port forwarding, no reverse proxy, no binding to other addresses). Requests from other websites are
rejected (`Origin` and `Sec-Fetch-Site` are checked), but this does not replace the loopback restriction.

## Supported versions

The latest release.

## Reporting a vulnerability

Please report vulnerabilities through GitHub's private vulnerability reporting on the repository
(https://github.com/lca-wrench/lca-wrench, tab "Security", "Report a vulnerability"), not through public issues. Include
the version, the steps to reproduce and the expected impact.
