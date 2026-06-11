FROM mcr.microsoft.com/devcontainers/rust:1-1.75-bookworm

ENV CARGO_HOME=/usr/local/cargo
ENV RUSTUP_HOME=/usr/local/rustup
ENV RUST_BACKTRACE=1

RUN rustup default stable && rustup component add rustfmt clippy

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
