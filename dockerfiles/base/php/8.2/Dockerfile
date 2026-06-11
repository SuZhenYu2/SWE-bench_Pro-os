FROM mcr.microsoft.com/devcontainers/php:1-8.2-bookworm

ENV COMPOSER_HOME=/usr/local/composer
ENV XDEBUG_MODE=coverage

RUN apt-get update && apt-get install -y \
    composer \
    phpunit \
    php-xdebug \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
