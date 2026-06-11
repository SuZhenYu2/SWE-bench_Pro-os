FROM mcr.microsoft.com/devcontainers/elixir:1-1.16-bookworm

ENV MIX_HOME=/usr/local/mix \
    HEX_HOME=/usr/local/hex \
    MIX_ENV=test

RUN mkdir -p /app /workspace ${MIX_HOME} ${HEX_HOME}

WORKDIR /app
