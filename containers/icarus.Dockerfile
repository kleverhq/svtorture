ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE} AS build

ARG TOOL_SHA
RUN test -n "$TOOL_SHA"
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       autoconf bison build-essential ca-certificates flex git gperf \
    && rm -rf /var/lib/apt/lists/*
RUN git init /src \
    && git -C /src remote add origin https://github.com/steveicarus/iverilog.git \
    && git -C /src fetch --depth=1 origin "$TOOL_SHA" \
    && git -C /src checkout --detach FETCH_HEAD
RUN cd /src \
    && sh autoconf.sh \
    && ./configure --prefix=/opt/iverilog \
    && make -j2 \
    && make install

FROM ${BASE_IMAGE}
ARG TOOL_SHA
LABEL org.opencontainers.image.source="https://github.com/steveicarus/iverilog"
LABEL org.opencontainers.image.revision="$TOOL_SHA"
LABEL org.opencontainers.image.licenses="GPL-2.0-or-later"
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       libbz2-1.0 libreadline8 zlib1g \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --no-create-home svtool
COPY --from=build /opt/iverilog /opt/iverilog
ENV PATH="/opt/iverilog/bin:${PATH}"
USER 10001:10001
ENTRYPOINT []
