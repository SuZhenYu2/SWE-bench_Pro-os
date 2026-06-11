FROM mcr.microsoft.com/devcontainers/go:1-1.23-bookworm

ENV GOPATH=/go
ENV GO111MODULE=on
ENV CGO_ENABLED=1
ENV GIN_MODE=test

RUN curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
