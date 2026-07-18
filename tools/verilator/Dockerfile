ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE} AS build

ARG TOOL_SHA
RUN test -n "$TOOL_SHA"
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       autoconf bison build-essential ca-certificates flex git help2man \
       libfl2 libfl-dev perl python3 \
    && rm -rf /var/lib/apt/lists/*
RUN git init /src \
    && git -C /src remote add origin https://github.com/verilator/verilator.git \
    && git -C /src fetch --depth=1 origin "$TOOL_SHA" \
    && git -C /src checkout --detach FETCH_HEAD
RUN cd /src \
    && autoconf \
    && ./configure --prefix=/opt/verilator \
    && make -j2 \
    && make install

FROM ${BASE_IMAGE}
ARG TOOL_SHA
LABEL org.opencontainers.image.source="https://github.com/verilator/verilator"
LABEL org.opencontainers.image.revision="$TOOL_SHA"
LABEL org.opencontainers.image.licenses="LGPL-3.0-only OR Artistic-2.0"
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       build-essential libfl2 perl python3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --no-create-home svtool
COPY --from=build /opt/verilator /opt/verilator
ENV PATH="/opt/verilator/bin:${PATH}"
ENV VERILATOR_ROOT="/opt/verilator/share/verilator"
USER 10001:10001
ENTRYPOINT []
