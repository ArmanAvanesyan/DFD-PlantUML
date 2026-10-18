# Exact same Java21 patch as the renderer, with compiler tools for Gradle.
ARG JDK_IMAGE
ARG RENDER_IMAGE
FROM ${JDK_IMAGE} AS jdk
FROM ${RENDER_IMAGE}
COPY --from=jdk /opt/java/openjdk /opt/java/openjdk
