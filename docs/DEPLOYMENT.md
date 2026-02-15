# Deployment Guide: Catenary Viewer Stack

This guide covers deploying the Catenary viewer stack on a Linux server (Ubuntu/Debian or Oracle Linux/RHEL).

## Prerequisites

- Linux server (Ubuntu 20.04+ / Debian 11+ / Oracle Linux 8+)
- 4GB+ RAM recommended
- 20GB+ disk space

---

## Quick Start (Ubuntu/Debian)

### 1. Install Dependencies

```bash
# Update and install required packages
sudo apt update
sudo apt install -y \
    protobuf-compiler \
    pkg-config \
    libssl-dev \
    build-essential \
    cmake \
    git \
    curl

# Install Rust (if not installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### 2. Clone and Build

```bash
# Clone the backend repo
git clone https://github.com/CatenaryTransit/catenary-backend.git
cd catenary-backend

# Build only the services you need (takes ~30 mins first time)
cargo build --release --bin maple    # GTFS ingestion
cargo build --release --bin harebell  # Tile server
cargo build --release --bin birch     # Search API (optional)
```

### 3. Start PostgreSQL with Docker

```bash
# Start PostgreSQL + PostGIS
docker run -d --name catenary_postgres \
    -e POSTGRES_USER=catenary \
    -e POSTGRES_PASSWORD=catenary \
    -e POSTGRES_DB=catenary \
    -p 5432:5432 \
    -v postgres_data:/var/lib/postgresql/data \
    postgis/postgis:16-3.4
```

### 4. Run Migrations

```bash
# Set database URL
export DATABASE_URL="postgres://catenary:catenary@localhost:5432/catenary"

# Install diesel CLI and run migrations
cargo install diesel_cli --no-default-features --features postgres
diesel migration run
```

### 5. Ingest GTFS Data (Maple)

```bash
# Run maple with your GTFS feed
./target/release/maple --gtfs /path/to/your-scotland-gtfs.zip
```

### 6. Start Tile Server (Harebell)

```bash
# Start the tile server
./target/release/harebell serve --port 8080 --address 0.0.0.0
```

### 7. Serve the Viewer

```bash
# Simple HTTP server for viewer.html
cd /path/to/catenary
python3 -m http.server 8081

# Or use nginx for production
```

---

## Alternative: Oracle Linux / RHEL

### 1. Install Dependencies

```bash
# For Oracle Linux / RHEL / CentOS
sudo dnf install -y \
    protobuf-compiler \
    pkg-config \
    openssl-devel \
    gcc \
    gcc-c++ \
    make \
    cmake \
    git \
    curl

# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
```

### 2. Build

```bash
git clone https://github.com/CatenaryTransit/catenary-backend.git
cd catenary-backend
cargo build --release --bin maple harebell birch
```

### 3. PostgreSQL

```bash
# Start PostgreSQL (same docker command works)
docker run -d --name catenary_postgres \
    -e POSTGRES_USER=catenary \
    -e POSTGRES_PASSWORD=catenary \
    -e POSTGRES_DB=catenary \
    -p 5432:5432 \
    postgis/postgis:16-3.4
```

---

## Using Docker Compose (Recommended)

### 1. Install Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $user

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 2. Clone and Run

```bash
# Clone this repo
git clone <this-repo> catenary
cd catenary

# Build and start services
docker compose up -d postgres harebell viewer

# To also run maple for ingestion
docker compose --profile ingest up -d maple
```

---

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Database |
| Harebell | 8080 | Tile server (MVT) |
| Birch | 3000 | Search API |
| Viewer | 8081 | Web UI |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgres://catenary:catenary@localhost:5432/catenary` | Database connection |
| `RUST_LOG` | `info` | Log level |

---

## Common Tasks

### Get GTFS Data

Place your Scotland GTFS zip file in `./gtfs/` or mount it:

```bash
docker run -v /path/to/gtfs:/gtfs:ro ...
```

### Check Database

```bash
docker exec -it catenary_postgres psql -U catenary -d catenary -c "SELECT COUNT(*) FROM gtfs.routes;"
```

### Check Tiles

```bash
curl -I http://localhost:8080/index.json
curl -I "http://localhost:8080/tiles/10/512/341.pbf"
```

---

## Troubleshooting

### Rust build fails with memory error

```bash
# Increase swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### PostgreSQL connection refused

```bash
# Check if container is running
docker ps | grep postgres

# Check logs
docker logs catenary_postgres
```

### Tiles not loading

- Verify Harebell is running: `curl http://localhost:8080/index.json`
- Check database has data: `SELECT COUNT(*) FROM gtfs.shapes;`
