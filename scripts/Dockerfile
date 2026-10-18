# Immutable renderer base plus signed packages from one dated Ubuntu snapshot.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG UBUNTU_SNAPSHOT=20261017T000000Z
USER root
RUN printf 'deb https://snapshot.ubuntu.com/ubuntu/%s/ jammy main universe\ndeb https://snapshot.ubuntu.com/ubuntu/%s/ jammy-updates main universe\ndeb https://snapshot.ubuntu.com/ubuntu/%s/ jammy-security main universe\n' "$UBUNTU_SNAPSHOT" "$UBUNTU_SNAPSHOT" "$UBUNTU_SNAPSHOT" > /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends libgd3 \
    && rm -rf /var/lib/apt/lists/* /usr/local/lib/graphviz/config* \
    && dot -c
