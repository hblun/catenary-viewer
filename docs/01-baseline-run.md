# Baseline Run Documentation

## Prerequisites

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
sudo apt install libprotoc-dev protobuf-compiler build-essential gcc pkg-config libssl-dev unzip wget cmake openssl libpq-dev

# Install COIN CBC integer linear programming solver (for routing - optional for viewer)
sudo apt-get install coinor-cbc coinor-libcbc-dev

# Install Postgres + PostGIS
sudo apt install postgresql-16 postgresql-16-postgis-3

# Enable PostGIS
sudo -u postgres psql -c "CREATE EXTENSION postgis;"
```

### Rust Toolchain

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# The project uses Rust edition 2024 - check rust-toolchain.toml for version
```

## Docker-Based Setup (Recommended)

### 1. Start PostGIS

```bash
cd backend/containers/common
docker compose up -d
```

This starts PostGIS 16 with PostGIS 3.4 on localhost:5432

Environment:
- POSTGRES_USER: catenary
- POSTGRES_PASSWORD: catenary  
- POSTGRES_DB: catenary

### 2. Environment Variables

```bash
export DATABASE_URL="postgres://catenary:catenary@localhost:5432/catenary"
export RUST_LOG=info
```

### 3. Run Migrations

The database schema is managed through Diesel. Run migrations:

```bash
cd backend
cargo install diesel_cli --no-default-features --features postgres
diesel migration run
```

Or migrations are typically run automatically by Maple on first ingest.

## Maple: GTFS Ingestion

### Command

```bash
cd backend
cargo run --bin maple -- --transitland /path/to/transitland-atlas
```

For UK-specific feeds, you can specify feeds directly:

```bash
cargo run --bin maple -- --help
```

### Expected Tables Created

Core tables in `gtfs` schema:
- `routes` - Route definitions with color, short_name, long_name, route_type, chateau
- `stops` - Stop definitions with point geometry, name, code
- `shapes` - Route geometries as LineString with color, route_label
- `trips` - Trip definitions
- `calendar` / `calendar_dates` - Service schedules
- `agencies` - Agency/operator info
- `chateaus` - Operator metadata with hull geometry

### Sample GTFS Feed

For testing, use a UK-specific GTFS feed:
- National Rail (UK) - available from various sources
- Transport for London (TfL) - https://api.tfl.gov.uk/gtfs/
- Scottish public transport feeds via Transport Scotland

## Harebell: Tile Generation

### Generate Tiles

```bash
# First, need to generate the transit graph (requires Gentian/Linnaea)
# For viewer-only, can generate simplified tiles directly from DB

cd backend

# Export tiles for a region
cargo run --bin harebell -- export --region uk

# This creates tiles in tiles_output/uk/
```

### Serve Tiles Locally

```bash
cargo run --bin harebell -- serve --address 127.0.0.1 --port 8080
```

Tile endpoints:
- `http://127.0.0.1:8080/tiles/{z}/{x}/{y}.pbf` - Vector tiles
- `http://127.0.0.1:8080/index.json` - TileJSON spec

### Tile Layers

Based on `harebell_viewer.html`:
- `transit` - Route lines (source-layer)
- `stations` - Stop points (source-layer)

## Frontend: Viewer

### Build

```bash
cd frontend
npm install
npm run build
```

### Development

```bash
npm run dev
```

The viewer connects to:
- Tile server: Configured in map setup (default: http://127.0.0.1:8080)
- API server (optional): Birch on port 3000

## Verification

### Check Database

```bash
psql -U catenary -h localhost -d catenary -c "SELECT COUNT(*) FROM gtfs.routes;"
psql -U catenary -h localhost -d catenary -c "SELECT COUNT(*) FROM gtfs.stops;"
psql -U catenary -h localhost -d catenary -c "SELECT COUNT(*) FROM gtfs.shapes;"
```

### Check Tiles

```bash
curl -I http://127.0.0.1:8080/index.json
curl -I "http://127.0.0.1:8080/tiles/10/512/341.pbf"
```

### Check Viewer

Open `harebell_viewer.html` directly in browser, or serve via:

```bash
cd backend
python3 -m http.server 8081
# Open http://localhost:8081/harebell_viewer.html
```
