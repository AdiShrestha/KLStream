# KLStream Multi-Stage Container Build

# Stage 1: Base Build Environment
FROM ubuntu:22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Builder & Test Runner
FROM base AS builder

WORKDIR /workspace

COPY . .

RUN cmake --preset release \
    && cmake --build --preset release --parallel \
    && ctest --preset release --output-on-failure

# Stage 3: Minimal Runtime Application
FROM ubuntu:22.04 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash klstream

WORKDIR /app

COPY --from=builder /workspace/build/release/source/apps/adaptive_window/adaptive_window_main /app/
COPY --from=builder /workspace/build/release/source/apps/adaptive_window/train_forest /app/
COPY --from=builder /workspace/build/release/source/examples/basic_pipeline /app/
COPY --from=builder /workspace/build/release/source/examples/ysb_pipeline /app/

RUN chown -R klstream:klstream /app

USER klstream

ENTRYPOINT ["/app/basic_pipeline"]
