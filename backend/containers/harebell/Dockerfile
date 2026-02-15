FROM debian:latest

RUN apt-get update && apt-get install -y curl
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup default stable

RUN apt install -y protobuf-compiler build-essential gcc pkg-config libssl-dev unzip wget libpq-dev

WORKDIR /catenary

COPY ./../.. .

RUN cargo build --release --bin harebell

RUN mkdir output-binaries/

RUN cp ./target/release/harebell ./output-binaries/

RUN rm -rf ./target/

CMD ["./output-binaries/harebell"]
