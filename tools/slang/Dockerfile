ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE} AS build

ARG TOOL_SHA
RUN test -n "$TOOL_SHA"
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       build-essential ca-certificates cmake git ninja-build python3 \
    && rm -rf /var/lib/apt/lists/*
RUN git init /src \
    && git -C /src remote add origin https://github.com/MikePopoloski/slang.git \
    && git -C /src fetch --depth=1 origin "$TOOL_SHA" \
    && git -C /src checkout --detach FETCH_HEAD
RUN cd /src \
    && cmake -S /src -B /src/build -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/opt/slang \
      -DSLANG_INCLUDE_TESTS=OFF \
      -DSLANG_INCLUDE_TOOLS=ON \
    && cmake --build /src/build -j2 \
    && cmake --install /src/build

FROM ${BASE_IMAGE}
ARG TOOL_SHA
LABEL org.opencontainers.image.source="https://github.com/MikePopoloski/slang"
LABEL org.opencontainers.image.revision="$TOOL_SHA"
LABEL org.opencontainers.image.licenses="MIT"
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       libstdc++6 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --no-create-home svtool
COPY --from=build /opt/slang /opt/slang
ENV PATH="/opt/slang/bin:${PATH}"
USER 10001:10001
ENTRYPOINT []
