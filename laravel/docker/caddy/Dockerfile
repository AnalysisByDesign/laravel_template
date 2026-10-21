# Caddy with the Route 53 DNS provider compiled in.
#
# The stock `caddy` image carries no DNS-challenge providers, and a
# wildcard certificate (`*.{{LOCAL_DOMAIN}}`) can ONLY be issued over the
# ACME DNS-01 challenge, so the provider has to be built in with xcaddy.
#
# Built and verified against Caddy v2.11.4 on 2026-07-27. The floating
# `2` tag is kept so a fresh build picks up patch releases; pin it to an
# exact version if a Caddy upgrade ever breaks issuance mid-week.
ARG CADDY_VERSION=2

FROM caddy:${CADDY_VERSION}-builder AS builder

RUN xcaddy build \
    --with github.com/caddy-dns/route53

FROM caddy:${CADDY_VERSION}

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
