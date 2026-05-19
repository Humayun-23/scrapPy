FROM alpine:latest

# Install curl and ca-certificates for downloading binaries
RUN apk add --no-cache curl ca-certificates bash

# Download the latest Hysteria2 binary from GitHub releases
RUN mkdir -p /usr/local/bin && \
    curl -L https://github.com/apernet/hysteria/releases/download/app%2Fv2.9.1/hysteria-linux-amd64 -o /usr/local/bin/hysteria && \
    chmod +x /usr/local/bin/hysteria

ENTRYPOINT ["hysteria"]
