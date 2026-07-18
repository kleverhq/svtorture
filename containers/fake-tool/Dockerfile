ARG BASE_IMAGE=python:3.12-slim-bookworm
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="SVTORTURE deterministic fake tool"
LABEL org.opencontainers.image.licenses="Apache-2.0"

COPY containers/fake-tool/fake_tool.py /usr/local/bin/fake-tool
RUN chmod 0555 /usr/local/bin/fake-tool \
    && useradd --system --uid 10001 --no-create-home fake

USER 10001:10001
ENTRYPOINT []
