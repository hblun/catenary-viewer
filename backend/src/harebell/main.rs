use actix_cors::Cors;
use actix_web::{web, App, HttpResponse, HttpServer, Responder};
use clap::Parser;
use std::path::PathBuf;
use std::sync::Arc;

mod config;
mod generator;
mod graph;
mod loader;
mod optimizer;
mod server;
mod tile_gen;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    #[command(subcommand)]
    cmd: Command,
}

#[derive(clap::Subcommand, Debug)]
enum Command {
    /// Serve tiles via HTTP
    Serve {
        #[arg(short, long, default_value = "127.0.0.1")]
        address: String,
        #[arg(short, long, default_value_t = 8080)]
        port: u16,
        #[arg(long, default_value = "tiles_output")]
        tiles_dir: PathBuf,
    },
    /// Export tiles for a region
    Export {
        /// Region to export (e.g., europe, north-america, japan)
        /// If not specified, loads globeflower_graph.bin
        #[arg(long)]
        region: Option<String>,
        #[arg(long)]
        graph_path: Option<PathBuf>,
        #[arg(long)]
        output_dir: Option<PathBuf>,
    },
}

#[tokio::main]
async fn main() -> std::io::Result<()> {
    dotenvy::dotenv().ok();
    env_logger::init();

    // Database Connection
    let database_url = std::env::var("DATABASE_URL").expect("DATABASE_URL must be set");
    let manager = diesel::r2d2::ConnectionManager::<diesel::pg::PgConnection>::new(database_url);
    let pool = diesel::r2d2::Pool::builder()
        .build(manager)
        .expect("Failed to create pool");

    // CLI Arguments
    let cli = Args::parse(); // Assuming Args is the new Cli and Command is Commands

    match cli.cmd {
        // Assuming cli.command is cli.cmd
        Command::Serve {
            port,
            address,
            tiles_dir,
        } => {
            println!("Starting static tile server on {}:{}", address, port);
            println!("Serving tiles from {}", tiles_dir.display());

            // Start Server
            HttpServer::new(move || {
                let cors = Cors::permissive();
                App::new()
                    .wrap(cors)
                    .app_data(web::Data::new(server::TileServerConfig {
                        tiles_dir: tiles_dir.clone(),
                    }))
                    // No more graph data needed
                    .configure(server::config)
            })
            .bind((address, port))?
            .run()
            .await
        }
        Command::Export {
            region,
            graph_path,
            output_dir,
        } => {
            println!("Starting Static MVT Generation...");

            // Determine graph file and output directory based on region
            let graph_file = match (&graph_path, &region) {
                (Some(path), _) => path.display().to_string(),
                (None, Some(r)) => {
                    let graph_file = format!("globeflower_graph_{}.bin", r);
                    println!("Processing region: {} (graph file: {})", r, graph_file);
                    graph_file
                }
                (None, None) => {
                    println!("No region specified, using default globeflower_graph.bin");
                    "globeflower_graph.bin".to_string()
                }
            };
            let output_dir = output_dir
                .map(|path| path.display().to_string())
                .unwrap_or_else(|| match &region {
                    Some(r) => format!("tiles_output/{}", r),
                    None => "tiles_output".to_string(),
                });

            // Load Graph
            let loader = loader::Loader::new(graph_file, pool);
            let mut graph = loader.load_graph().await.map_err(|e: anyhow::Error| {
                std::io::Error::new(std::io::ErrorKind::Other, e.to_string())
            })?;

            println!(
                "Graph loaded. {} edges, {} nodes",
                graph.edges.len(),
                graph.nodes.len()
            );

            // NYC Route Grouping is now handled automatically by loader (group by color)

            // Run Optimizer
            let optimizer = optimizer::Optimizer::new();
            optimizer.optimize(&mut graph);

            println!("Rebuilding spatial indices after optimization...");
            graph.rebuild_indices();

            println!("Generating tiles to {}...", output_dir);

            let generator = generator::Generator::new(output_dir);
            generator
                .generate_all(&graph, 5, 16)
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;

            println!("Generation Complete!");
            Ok(())
        }
    }
}

async fn index() -> impl Responder {
    HttpResponse::Ok().body("Harebell Tile Server")
}
