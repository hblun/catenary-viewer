use actix_web::{get, web, HttpResponse, Responder};
use std::fs;
use std::path::PathBuf;

#[derive(Clone)]
pub struct TileServerConfig {
    pub tiles_dir: PathBuf,
}

pub fn config(cfg: &mut web::ServiceConfig) {
    cfg.service(get_tile);
}

#[get("/tiles/{z}/{x}/{y}.pbf")]
async fn get_tile(
    path: web::Path<(u8, u32, u32)>,
    config: web::Data<TileServerConfig>,
) -> impl Responder {
    let (z, x, y) = path.into_inner();
    let file_path = config
        .tiles_dir
        .join(z.to_string())
        .join(x.to_string())
        .join(format!("{}.pbf", y));

    if file_path.exists() {
        match fs::read(&file_path) {
            Ok(bytes) => HttpResponse::Ok()
                .content_type("application/x-protobuf")
                .body(bytes),
            Err(_) => HttpResponse::InternalServerError().finish(),
        }
    } else {
        HttpResponse::NotFound().finish()
    }
}
