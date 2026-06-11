FROM mcr.microsoft.com/devcontainers/rust:1-1-bookworm

ENV CARGO_HOME=/usr/local/cargo \
    RUSTUP_HOME=/usr/local/rustup \
    RUST_BACKTRACE=1

RUN rustup default stable && \
    rustup component add rustfmt clippy && \
    cargo --version && \
    rustc --version && \
    rustfmt --version && \
    cargo clippy --version

WORKDIR /app
WORKDIR /workspace
