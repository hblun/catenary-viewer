.PHONY: help build run-db run-maple run-harebell run-birch run-viewer stop clean

help:
	@echo "Catenary Viewer Stack - Make Commands"
	@echo ""
	@echo "  make run-db        - Start PostgreSQL container"
	@echo "  make build         - Build all binaries (maple, harebell, birch)"
	@echo "  make run-maple     - Run maple (ingests GTFS)"
	@echo "  make run-harebell  - Run harebell (tile server)"
	@echo "  make run-birch     - Run birch (API server)"
	@echo "  make run-viewer    - Run viewer HTTP server"
	@echo "  make stop          - Stop all containers"
	@echo "  make clean         - Clean build artifacts"

run-db:
	docker run -d --name catenary_postgres \
		-e POSTGRES_USER=catenary \
		-e POSTGRES_PASSWORD=catenary \
		-e POSTGRES_DB=catenary \
		-p 5432:5432 \
		-v postgres_data:/var/lib/postgresql/data \
		postgis/postgis:16-3.4

build:
	cd backend && cargo build --release --bin maple
	cd backend && cargo build --release --bin harebell
	cd backend && cargo build --release --bin birch

run-maple:
	@echo "Usage: DATABASE_URL=postgres://catenary:catenary@localhost:5432/catenary ./backend/target/release/maple --gtfs /path/to/gtfs.zip"

run-harebell:
	cd backend && ./target/release/harebell serve --port 8080 --address 0.0.0.0

run-birch:
	cd backend && ./target/release/birch

run-viewer:
	cd .. && python3 -m http.server 8081

stop:
	docker stop $$(docker ps -q --filter "name=catenary") 2>/dev/null || true

clean:
	cd backend && cargo clean
