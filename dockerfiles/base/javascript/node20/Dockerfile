FROM mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm

ENV NODE_ENV=test \
    CI=true

RUN npm install -g npm@latest yarn@1.22.22 pnpm@8 typescript@5 vitest@1 jest@29 mocha@10

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
