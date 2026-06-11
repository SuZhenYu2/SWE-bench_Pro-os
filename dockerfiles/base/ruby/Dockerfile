FROM mcr.microsoft.com/devcontainers/ruby:1-3.2-bookworm

ENV BUNDLE_PATH=/usr/local/bundle \
    RAILS_ENV=test

RUN gem install bundler:2.5.0 && \
    gem install rspec minitest && \
    ruby --version && \
    bundle --version && \
    rspec --version

WORKDIR /app
WORKDIR /workspace
