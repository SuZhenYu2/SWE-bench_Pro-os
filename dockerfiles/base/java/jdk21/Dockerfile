FROM mcr.microsoft.com/devcontainers/java:1-21-bookworm

ENV JAVA_HOME=/usr/local/sdkman/candidates/java/current \
    MAVEN_OPTS="-Xmx2g"

RUN apt-get update && \
    apt-get install -y --no-install-recommends maven gradle && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /usr/local/lib && \
    curl -L -o /usr/local/lib/junit-platform-console-standalone.jar \
        https://repo1.maven.org/maven2/org/junit/platform/junit-platform-console-standalone/1.10.0/junit-platform-console-standalone-1.10.0.jar

WORKDIR /app
RUN mkdir -p /workspace

CMD ["bash"]
