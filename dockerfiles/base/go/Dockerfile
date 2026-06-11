FROM mcr.microsoft.com/devcontainers/go:1-1.22-bookworm

ENV GOPATH=/go
ENV GO111MODULE=on
ENV CGO_ENABLED=1
ENV GIN_MODE=test

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /go/bin && chmod -R 777 /go

ENV PATH="/go/bin:/usr/local/go/bin:${PATH}"

RUN go version && \
    go install golang.org/x/tools/cmd/goimports@latest || true

ARG GOLANGCI_LINT_VERSION=v1.55.2
RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b /usr/local/bin ${GOLANGCI_LINT_VERSION}

RUN mkdir -p /app /workspace && chown -R vscode:vscode /app /workspace /go

USER vscode

WORKDIR /app
