use std::env;
use std::path::PathBuf;

fn main() {
    if let Ok(manifest_dir) = env::var("CARGO_MANIFEST_DIR") {
        let pylibs = PathBuf::from(manifest_dir).join("pylibs");
        println!("cargo:rustc-link-search=native={}", pylibs.display());
    }
}
