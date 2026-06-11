FROM mcr.microsoft.com/devcontainers/cpp:1-1-bookworm

RUN apt-get update && apt-get install -y \
    gcc-11 \
    g++-11 \
    cmake \
    make \
    libgtest-dev \
    libboost-test-dev \
    catch2 \
    && rm -rf /var/lib/apt/lists/*

ENV CC=gcc
ENV CXX=g++
ENV CTEST_OUTPUT_ON_FAILURE=1

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
