FROM mcr.microsoft.com/devcontainers/ruby:1-3.1-bookworm

ENV BUNDLE_PATH=/usr/local/bundle
ENV RAILS_ENV=test

RUN gem install bundler rspec minitest

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
