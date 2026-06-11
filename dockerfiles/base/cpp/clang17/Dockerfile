FROM mcr.microsoft.com/devcontainers/cpp:1-1-bookworm

RUN apt-get update && apt-get install -y \
    clang-17 \
    cmake \
    make \
    libgtest-dev \
    libboost-test-dev \
    catch2 \
    && rm -rf /var/lib/apt/lists/*

ENV CC=clang
ENV CXX=clang++
ENV CTEST_OUTPUT_ON_FAILURE=1

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
