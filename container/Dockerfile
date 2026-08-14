# syntax=docker/dockerfile:1
FROM golang:1.25.6-bookworm AS proxy-build
WORKDIR /src
COPY container/once-proxy.go .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags='-s -w' -o /once-proxy once-proxy.go

FROM vaultwarden/server:1.35.4
USER root

ARG LITESTREAM_VERSION=0.5.5
ARG HIVEMIND_VERSION=1.1.0
ARG LITESTREAM_SHA256=47ff03852c56d0af896eb890ed3ab006fd9916d80698186a494cfd6b4c8ded63
ARG HIVEMIND_SHA256=809ca1c5fedbbfca8fdfb3a4b9bb9c41868b046f35f85a3e893ccf2583a3921a

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl gzip sqlite3 \
 && curl -fsSL "https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-${LITESTREAM_VERSION}-linux-x86_64.tar.gz" -o /tmp/litestream.tar.gz \
 && echo "${LITESTREAM_SHA256}  /tmp/litestream.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/litestream.tar.gz -C /usr/local/bin litestream \
 && curl -fsSL "https://github.com/DarthSim/hivemind/releases/download/v${HIVEMIND_VERSION}/hivemind-v${HIVEMIND_VERSION}-linux-amd64.gz" -o /tmp/hivemind.gz \
 && echo "${HIVEMIND_SHA256}  /tmp/hivemind.gz" | sha256sum -c - \
 && gzip -dc /tmp/hivemind.gz > /usr/local/bin/hivemind \
 && chmod 0755 /usr/local/bin/hivemind /usr/local/bin/litestream \
 && rm -rf /var/lib/apt/lists/* /tmp/litestream.tar.gz /tmp/hivemind.gz

COPY --from=proxy-build /once-proxy /usr/local/bin/once-proxy
COPY container/Procfile container/litestream.yml /etc/vaultwarden/
COPY container/entrypoint container/restore-check /usr/local/bin/
RUN chmod 0755 /usr/local/bin/entrypoint /usr/local/bin/restore-check /usr/local/bin/once-proxy

ENV DATA_FOLDER=/storage \
    ROCKET_ADDRESS=127.0.0.1 \
    ROCKET_PORT=8080 \
    LITESTREAM_CONFIG=/etc/vaultwarden/litestream.yml
EXPOSE 80
ENTRYPOINT ["/usr/local/bin/entrypoint"]
