FROM debian:latest

RUN apt-get update && apt-get install -y curl
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup default stable

RUN apt install -y protobuf-compiler build-essential gcc pkg-config libssl-dev unzip wget libpq-dev cmake

# Install diesel CLI for migrations
RUN cargo install diesel_cli --no-default-features --features postgres

WORKDIR /build

COPY . .

# Override x86-specific CPU flags for ARM64
RUN CFLAGS="-march=armv8-a" CXXFLAGS="-march=armv8-a" RUSTFLAGS="-C target-cpu=generic" cargo build --release --bin maple

RUN mkdir -p /output && cp ./target/release/maple /output/

CMD ["/output/maple"]