FROM mcr.microsoft.com/devcontainers/java:1-17-bookworm

ENV JAVA_HOME=/usr/local/sdkman/candidates/java/current
ENV MAVEN_OPTS="-Xmx2g -XX:MaxMetaspaceSize=512m"

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

ARG MAVEN_VERSION=3.9.6
RUN mkdir -p /opt/maven && \
    curl -fsSL https://archive.apache.org/dist/maven/maven-3/${MAVEN_VERSION}/binaries/apache-maven-${MAVEN_VERSION}-bin.tar.gz | tar -xzC /opt/maven && \
    ln -s /opt/maven/apache-maven-${MAVEN_VERSION}/bin/mvn /usr/local/bin/mvn

ARG GRADLE_VERSION=8.5
RUN mkdir -p /opt/gradle && \
    curl -fsSL https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip -o /tmp/gradle.zip && \
    unzip -q /tmp/gradle.zip -d /opt/gradle && \
    rm /tmp/gradle.zip && \
    ln -s /opt/gradle/gradle-${GRADLE_VERSION}/bin/gradle /usr/local/bin/gradle

ARG JUNIT_PLATFORM_VERSION=1.10.2
RUN mkdir -p /opt/junit && \
    curl -fsSL https://repo1.maven.org/maven2/org/junit/platform/junit-platform-console-standalone/${JUNIT_PLATFORM_VERSION}/junit-platform-console-standalone-${JUNIT_PLATFORM_VERSION}.jar -o /opt/junit/junit-platform-console-standalone.jar && \
    chmod 644 /opt/junit/junit-platform-console-standalone.jar

ENV M2_HOME=/opt/maven/apache-maven-${MAVEN_VERSION}
ENV GRADLE_HOME=/opt/gradle/gradle-${GRADLE_VERSION}

WORKDIR /workspace

RUN mkdir -p /app /workspace && chown -R vscode:vscode /app /workspace

USER vscode

WORKDIR /app
