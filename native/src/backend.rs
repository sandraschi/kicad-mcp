use std::fs::OpenOptions;
use std::io::{BufRead, BufReader, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::str::FromStr;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::path::BaseDirectory;
use tauri::{AppHandle, Emitter, Manager};

pub struct BackendProcess(pub Mutex<Option<Child>>);

const BACKEND_NAME: &str = "kicad-mcp-backend.exe";
const BACKEND_PORT: u16 = 11016;

fn dev_backend_path() -> Option<PathBuf> {
    if !cfg!(debug_assertions) { return None; }
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("binaries").join(BACKEND_NAME);
    path.exists().then_some(path)
}

fn log_line(app: &AppHandle, message: &str) {
    eprintln!("[backend] {message}");
    if let Ok(dir) = app.path().app_log_dir() {
        let _ = std::fs::create_dir_all(&dir);
        let log_path = dir.join("backend-spawn.log");
        if let Ok(mut file) = OpenOptions::new().create(true).append(true).open(log_path) {
            let _ = writeln!(file, "{message}");
        }
    }
}

fn resolve_bundled_backend(app: &AppHandle) -> Result<PathBuf, String> {
    let mut tried = Vec::new();
    if let Ok(path) = app.path().resolve(BACKEND_NAME, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() { return Ok(path); }
    }
    let resources_path = format!("resources/{BACKEND_NAME}");
    if let Ok(path) = app.path().resolve(&resources_path, BaseDirectory::Resource) {
        tried.push(path.display().to_string());
        if path.exists() { return Ok(path); }
    }
    Err(format!("bundled backend missing (tried: {})", tried.join("; ")))
}

pub fn materialize_backend(app: &AppHandle) -> Result<PathBuf, String> {
    if let Some(dev_path) = dev_backend_path() {
        log_line(app, &format!("using dev backend: {}", dev_path.display()));
        return Ok(dev_path);
    }
    let bundled = resolve_bundled_backend(app)?;
    log_line(app, &format!("using bundled backend: {}", bundled.display()));
    Ok(bundled)
}

pub fn spawn_backend(app: AppHandle, state: &BackendProcess) -> Result<String, String> {
    // Kill any managed child from a previous run
    if let Some(mut child) = state.0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }

    // Kill any stale backend process by image name
    let _ = Command::new("taskkill.exe")
        .args(["/F", "/IM", "kicad-mcp-backend.exe", "/T"])
        .stdout(Stdio::null()).stderr(Stdio::null())
        .status();

    let backend_path = materialize_backend(&app)?;
    log_line(&app, &format!("spawning {} on port {}", backend_path.display(), BACKEND_PORT));

    let child = Command::new(&backend_path)
        .args(["--mode", "http", "--port", "11016"])
        .env("KICAD_TAURI", "1")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|e| format!("spawn failed: {e}"))?;
    state.0.lock().unwrap().replace(child);

    let addr = SocketAddr::from_str("127.0.0.1:11016").unwrap();
    let app_health = app.clone();
    thread::spawn(move || {
        for _attempt in 0..30 {
            thread::sleep(Duration::from_secs(2));
            if TcpStream::connect_timeout(&addr, Duration::from_secs(2)).is_ok() {
                let _ = app_health.emit("backend-status", "ready");
                return;
            }
        }
        let _ = app_health.emit("backend-status", "error: backend not reachable");
    });

    Ok("Backend starting".into())
}
