FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN pip install --no-cache-dir pipx && \
    pip install --no-cache-dir pytest tox poetry virtualenv

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
