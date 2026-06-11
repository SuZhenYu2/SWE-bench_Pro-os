FROM mcr.microsoft.com/devcontainers/cpp:1-1-bookworm

ENV CC=gcc \
    CXX=g++ \
    CTEST_OUTPUT_ON_FAILURE=1

RUN apt-get update && \
    apt-get install -y \
        gcc-12 \
        g++-12 \
        cmake \
        make \
        libgtest-dev \
        libboost-test-dev && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 100 && \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 100 && \
    update-alternatives --set gcc /usr/bin/gcc-12 && \
    update-alternatives --set g++ /usr/bin/g++-12 && \
    cd /usr/src/googletest && \
    cmake . && \
    make && \
    cp lib/*.a /usr/lib/ && \
    rm -rf /var/lib/apt/lists/* && \
    gcc --version && \
    g++ --version && \
    cmake --version

WORKDIR /app
WORKDIR /workspace
