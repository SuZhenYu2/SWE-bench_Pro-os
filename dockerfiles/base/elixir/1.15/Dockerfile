FROM mcr.microsoft.com/devcontainers/elixir:1-1.15-bookworm

ENV MIX_HOME=/usr/local/mix
ENV HEX_HOME=/usr/local/hex
ENV MIX_ENV=test

RUN mix local.hex --force && mix local.rebar --force

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
