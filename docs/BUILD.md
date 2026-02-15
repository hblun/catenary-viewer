# Build with Docker/Podman

Due to compatibility issues with Apple Silicon (arm64) and some native dependencies, it's easier to build the backend using Docker/Podman.

## Option 1: Build harebell binary only

```bash
# Build just harebell (tile server)
cd backend

# Using Podman
podman run --rm -v $(pwd):/src -w /src rust:1.80 \
  sh -c "apt-get update && apt-get install -y protobuf-compiler pkg-config libssl-dev && cargo build --release -p harebell"

# Or using Docker
docker run --rm -v $(pwd):/src -w /src rust:1.80 \
  sh -c "apt-get update && apt-get install -y protobuf-compiler pkg-config libssl-dev && cargo build --release -p harebell"
```

## Option 2: Full development environment

Use the existing Docker setup from the backend:

```bash
cd backend/containers/common
podman-compose up -d
```

## Option 3: Native build (requires fixes)

The codebase needs fixes for:
1. `fasthash-sys` - x86 CPU flags on ARM
2. `ring` - CPU feature detection on newer macOS

These require modifying `Cargo.toml` dependencies or using older macOS versions.

## Recommended: Use pre-built binaries

Check if the Catenary project releases pre-built binaries:
https://github.com/CatenaryTransit/catenary-backend/releases
