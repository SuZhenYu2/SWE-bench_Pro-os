FROM mcr.microsoft.com/devcontainers/php:1-8.2-bookworm

ENV COMPOSER_HOME=/usr/local/composer \
    XDEBUG_MODE=coverage

RUN mkdir -p /app /workspace ${COMPOSER_HOME}

RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer --2 \
    && chmod +x /usr/local/bin/composer

RUN pecl install xdebug \
    && docker-php-ext-enable xdebug

RUN composer global require --dev phpunit/phpunit:^10 \
    && ln -sf ${COMPOSER_HOME}/vendor/bin/phpunit /usr/local/bin/phpunit

WORKDIR /app
