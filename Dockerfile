# =============================================================================
# KLStream Development Container
# Multi-stage build for x86_64 Linux
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base Development Image
# -----------------------------------------------------------------------------
FROM --platform=linux/amd64 ubuntu:22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install essential build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ninja-build \
    git \
    gdb \
    valgrind \
    clang-14 \
    clang-format-14 \
    clang-tidy-14 \
    lldb-14 \
    libc++-14-dev \
    libc++abi-14-dev \
    libstdc++-11-dev \
    ca-certificates \
    curl \
    wget \
    vim \
    htop \
    linux-tools-generic \
    && rm -rf /var/lib/apt/lists/*

# Set up alternatives for clang tools
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-14 100 \
    && update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-14 100 \
    && update-alternatives --install /usr/bin/clang-format clang-format /usr/bin/clang-format-14 100 \
    && update-alternatives --install /usr/bin/clang-tidy clang-tidy /usr/bin/clang-tidy-14 100 \
    && update-alternatives --install /usr/bin/lldb lldb /usr/bin/lldb-14 100

# Create non-root user for development
ARG USERNAME=dev
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Stage 2: Development Image
# -----------------------------------------------------------------------------
FROM base AS development

WORKDIR /workspace

# Set compiler environment
ENV CC=gcc
ENV CXX=g++

# Copy project files
COPY --chown=${USERNAME}:${USERNAME} . .

USER $USERNAME

# Default command
CMD ["/bin/bash"]

# -----------------------------------------------------------------------------
# Stage 3: Builder Image
# -----------------------------------------------------------------------------
FROM base AS builder

WORKDIR /workspace

COPY . .

# Build with Release configuration
RUN cmake -B build -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DKLSTREAM_BUILD_TESTS=ON \
    -DKLSTREAM_BUILD_BENCHMARKS=ON \
    -DKLSTREAM_BUILD_EXAMPLES=ON \
    -DKLSTREAM_ENABLE_LTO=ON \
    && cmake --build build --parallel

# Run tests
RUN cd build && ctest --output-on-failure

# -----------------------------------------------------------------------------
# Stage 4: Production Runtime Image (minimal)
# -----------------------------------------------------------------------------
FROM --platform=linux/amd64 ubuntu:22.04 AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy built artifacts
COPY --from=builder /workspace/build/klstream_example_pipeline /app/

# Create non-root user for runtime
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

ENTRYPOINT ["/app/klstream_example_pipeline"]
