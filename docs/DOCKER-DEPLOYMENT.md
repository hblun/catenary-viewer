# Deployment Guide: Catenary Viewer Stack (Docker)

This guide covers deploying the Catenary viewer stack using Docker on a Linux server.

## Prerequisites

- Linux server (Ubuntu 20.04+ / Debian 11+ / Oracle Linux 8+)
- Docker or Podman installed
- 4GB+ RAM recommended
- 20GB+ disk space

---

## Quick Start

### 1. Clone and Setup

```bash
git clone <this-repo> catenary
cd catenary
```

### 2. Build and Start

```bash
# Build all services (first time takes ~30 mins)
docker compose build

# Start all services
docker compose up -d
```

### 3. Ingest GTFS

```bash
# Copy your GTFS file to the gtfs folder
cp /path/to/scotland-gtfs.zip ./gtfs/

# Run maple to ingest
docker compose run --rm maple --gtfs /gtfs/scotland-gtfs.zip
```

### 4. View the Map

Open http://your-server-ip:8081

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| **postgres** | 5432 | PostgreSQL + PostGIS |
| **harebell** | 8080 | Tile server (MVT) |
| **birch** | 3000 | Search API |
| **viewer** | 8081 | Web UI |

---

## Common Commands

```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# Start specific services
docker compose up -d postgres harebell viewer

# View logs
docker compose logs -f harebell

# Stop all
docker compose down

# Run maple (ingest GTFS)
docker compose run --rm maple --gtfs /gtfs/my-gtfs.zip

# Check database
docker compose exec postgres psql -U catenary -d catenary -c "SELECT COUNT(*) FROM gtfs.routes;"
```

---

## Data

### GTFS Input

Mount your GTFS zip file to `./gtfs/`:

```yaml
# docker-compose.yml
volumes:
  - ./gtfs:/gtfs:ro
```

Then run:
```bash
docker compose run --rm maple --gtfs /gtfs/scotland-gtfs.zip
```

---

## Configuration

### Environment Variables

Create a `.env` file:

```bash
DATABASE_URL=postgres://catenary:catenary@postgres:5432/catenary
RUST_LOG=info
```

### Customise Ports

Edit `docker-compose.yml`:

```yaml
services:
  harebell:
    ports:
      - "8080:8080"  # Change host port
```

---

## Troubleshooting

### Build fails

```bash
# Clean and rebuild
docker compose build --no-cache
```

### Tiles not loading

```bash
# Check harebell logs
docker compose logs harebell

# Check database has data
docker compose exec postgres psql -U catenary -d catenary -c "SELECT COUNT(*) FROM gtfs.shapes;"
```

### PostgreSQL connection

```bash
# Check postgres is running
docker compose ps

# Check logs
docker compose logs postgres
```
