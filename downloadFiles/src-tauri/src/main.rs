// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::HashMap;
use std::net::TcpListener;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{path::BaseDirectory, Manager, WindowEvent};
use std::io::{BufRead, BufReader};
use std::thread;
use std::time::Instant;

/// Lê um arquivo .env e retorna um HashMap com as chaves e valores.
/// Ignora linhas vazias e comentários (que começam com #).
fn load_env_file(path: &std::path::Path) -> HashMap<String, String> {
    let mut map = HashMap::new();
    if let Ok(content) = std::fs::read_to_string(path) {
        for line in content.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            if let Some((key, value)) = line.split_once('=') {
                map.insert(key.trim().to_string(), value.trim().to_string());
            }
        }
        println!("[Tauri] .env carregado de {:?} ({} variáveis)", path, map.len());
    } else {
        eprintln!("[Tauri] AVISO: Não foi possível ler .env em {:?}", path);
    }
    map
}

#[cfg(windows)]
use std::os::windows::process::CommandExt;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x08000000;

struct BackendProcess {
    api: Option<Child>,
    worker: Option<Child>,
    node: Option<Child>,
}

fn is_port_free(port: u16) -> bool {
    TcpListener::bind(("127.0.0.1", port)).is_ok()
}

impl BackendProcess {
    fn kill_all(&mut self) {
        let start = Instant::now();
        println!("[Tauri] Encerrando todos os processos de backend...");

        // Mata todos os processos em paralelo usando threads
        let api = self.api.take();
        let worker = self.worker.take();
        let node = self.node.take();

        let handles: Vec<_> = [
            ("API", api),
            ("Worker", worker),
            ("Node", node),
        ]
        .into_iter()
        .filter_map(|(name, child)| {
            child.map(|mut c| {
                thread::spawn(move || {
                    let _ = c.kill();
                    let _ = c.wait(); // Evita processos zumbis
                    println!("[Tauri] {} encerrado.", name);
                })
            })
        })
        .collect();

        for h in handles {
            let _ = h.join();
        }
        println!("[Tauri] Todos os processos encerrados em {:?}", start.elapsed());
    }
}

fn spawn_and_log(mut command: Command, name: &'static str) -> std::io::Result<Child> {
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    #[cfg(windows)]
    command.creation_flags(CREATE_NO_WINDOW);

    let mut child = command.spawn()?;

    if let Some(stdout) = child.stdout.take() {
        thread::spawn(move || {
            let reader = BufReader::with_capacity(8192, stdout);
            for line in reader.lines() {
                if let Ok(l) = line {
                    println!("[{}] {}", name, l);
                }
            }
        });
    }

    if let Some(stderr) = child.stderr.take() {
        thread::spawn(move || {
            let reader = BufReader::with_capacity(8192, stderr);
            for line in reader.lines() {
                if let Ok(l) = line {
                    if l.to_lowercase().contains("error") {
                        eprintln!("[{} ERROR] {}", name, l);
                    } else {
                        println!("[{} Log] {}", name, l);
                    }
                }
            }
        });
    }

    Ok(child)
}

fn main() {

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(Mutex::new(BackendProcess {
            api: None,
            worker: None,
            node: None,
        }))
        .setup(|app| {
            let startup_time = Instant::now();
            let handle = app.handle();
            let state = handle.state::<Mutex<BackendProcess>>();

            // 1. Tratar paths de forma robusta para Tauri 2.0
            let resolve_path = |path: &str| {
                if let Ok(p) = handle.path().resolve(path, BaseDirectory::Resource) {
                    if p.exists() { return p; }
                }
                if let Ok(p) = handle.path().resolve(format!("_up_/backend/{}", path), BaseDirectory::Resource) {
                    if p.exists() { return p; }
                }
                handle.path().resolve(path, BaseDirectory::Resource).unwrap()
            };

            let (python_dir, node_dir, node_env_file) = if cfg!(debug_assertions) {
                let mut base = std::env::current_dir().unwrap();
                if base.ends_with("src-tauri") {
                    base = base.parent().unwrap().to_path_buf();
                }
                (
                    base.join("backend/pythonservice"),
                    base.join("backend/node_service"),
                    base.join("backend/node_service/.env"),
                )
            } else {
                (
                    resolve_path("pythonservice"),
                    resolve_path("node_service/dist"),
                    resolve_path("node_service/.env"),  // Caminho correto do recurso
                )
            };

            // Carregar variáveis do .env do Node Service
            let node_env_vars = load_env_file(&node_env_file);

            let normalize = |p: std::path::PathBuf| -> String {
                let s = p.to_string_lossy().to_string();
                let path = if s.starts_with(r"\\?\") {
                    s[4..].to_string()
                } else {
                    s
                };
                path.replace("/", "\\")
            };

            let python_dir_str = normalize(python_dir.clone());
            let node_dir_str = normalize(node_dir.clone());

            println!("[Tauri] Python Dir: {}", python_dir_str);
            println!("[Tauri] Node Dir: {}", node_dir_str);

            let python_bin_dir = if cfg!(debug_assertions) {
                "".to_string()
            } else {
                normalize(resolve_path("bin/python"))
            };

            let python_bin = if cfg!(debug_assertions) {
                "python".to_string()
            } else {
                normalize(resolve_path("bin/python/python.exe"))
            };

            let node_bin = if cfg!(debug_assertions) {
                "node".to_string()
            } else {
                normalize(resolve_path("bin/node/node.exe"))
            };

            // cria processos paralelos para diminuir o tempo de start, entao ele cria clones dos processos e envia -
            // para threads separadas assim diminuindo esse tempo.

            let python_dir_api = python_dir.clone();
            let python_dir_str_api = python_dir_str.clone();
            let python_bin_dir_api = python_bin_dir.clone();
            let python_bin_api = python_bin.clone();

            let python_dir_worker = python_dir.clone();
            let python_dir_str_worker = python_dir_str.clone();
            let python_bin_dir_worker = python_bin_dir.clone();
            let python_bin_worker = python_bin.clone();

            let node_dir_spawn = node_dir.clone();
            let node_bin_spawn = node_bin.clone();
            let node_env_vars_spawn = node_env_vars.clone();

            // Thread 1: Python API
            let api_handle = thread::spawn(move || -> Option<Child> {
                if !python_dir_api.exists() {
                    eprintln!("[Tauri] Erro: Diretório da API Python não encontrado em {:?}", python_dir_api);
                    return None;
                }
                if !is_port_free(8000) {
                    eprintln!("[Tauri] AVISO: Porta 8000 já está em uso. Assumindo que a API já está rodando.");
                    return None;
                }

                let mut cmd = Command::new(&python_bin_api);
                cmd.current_dir(&python_dir_api);
                cmd.env("PYTHONPATH", &python_dir_str_api);

                if !python_bin_dir_api.is_empty() {
                    cmd.env("PYTHONHOME", &python_bin_dir_api);
                    if let Ok(existing_path) = std::env::var("PATH") {
                        cmd.env("PATH", format!("{};{}", python_bin_dir_api, existing_path));
                    }
                }

                cmd.args(["bootstrap_api.py"]);
                // As variáveis de ambiente devem ser lidas dos arquivos .env pelo próprio serviço Python

                match spawn_and_log(cmd, "Python-API") {
                    Ok(child) => Some(child),
                    Err(e) => {
                        eprintln!("[Tauri] Falha ao iniciar Python-API: {}", e);
                        None
                    }
                }
            });

            // Thread 2: Node Service
            let node_handle = thread::spawn(move || -> Option<Child> {
                if !node_dir_spawn.exists() {
                    eprintln!("[Tauri] Erro: Diretório do Node Service não encontrado em {:?}", node_dir_spawn);
                    return None;
                }
                if !is_port_free(3000) {
                    eprintln!("[Tauri] AVISO: Porta 3000 já está em uso. Assumindo que o Node Service já está rodando.");
                    return None;
                }

                let node_cmd = if cfg!(debug_assertions) {
                    let mut cmd = Command::new("cmd");
                    cmd.current_dir(&node_dir_spawn).args(["/c", "npx", "ts-node", "server.ts"]);
                    cmd
                } else {
                    let (run_dir, script) = if node_dir_spawn.join("index.js").exists() {
                        (node_dir_spawn.clone(), "index.js")
                    } else if node_dir_spawn.join("server.js").exists() {
                        (node_dir_spawn.clone(), "server.js")
                    } else if node_dir_spawn.join("dist/index.js").exists() {
                        (node_dir_spawn.join("dist"), "index.js")
                    } else if node_dir_spawn.join("dist/server.js").exists() {
                        (node_dir_spawn.join("dist"), "server.js")
                    } else {
                        (node_dir_spawn.clone(), "server.js")
                    };

                    println!("[Tauri] Iniciando Node em: {:?} com script: {}", run_dir, script);

                    let mut cmd = Command::new(&node_bin_spawn);
                    cmd.current_dir(&run_dir);
                    // Injetar variáveis do .env lido em runtime
                    for (key, val) in &node_env_vars_spawn {
                        cmd.env(key, val);
                    }
                    cmd.args([script]);
                    cmd
                };

                match spawn_and_log(node_cmd, "Node-Service") {
                    Ok(child) => Some(child),
                    Err(e) => {
                        eprintln!("[Tauri] Falha CRÍTICA ao iniciar Node-Service: {}. Pasta: {:?}", e, node_dir_spawn);
                        None
                    }
                }
            });

            // Thread 3: Python Worker
            let worker_handle = thread::spawn(move || -> Option<Child> {
                if !python_dir_worker.exists() {
                    eprintln!("[Tauri] Erro: Diretório do Worker Python não encontrado em {:?}", python_dir_worker);
                    return None;
                }

                let mut worker_cmd = Command::new(&python_bin_worker);
                worker_cmd.current_dir(&python_dir_worker);

                let python_path = vec![
                    python_dir_str_worker.clone(),
                    format!("{}/Lib/site-packages", python_bin_dir_worker),
                    format!("{}/python312.zip", python_bin_dir_worker),
                ];
                worker_cmd.env("PYTHONPATH", python_path.join(";"));

                if !python_bin_dir_worker.is_empty() {
                    worker_cmd.env("PYTHONHOME", &python_bin_dir_worker);
                    if let Ok(existing_path) = std::env::var("PATH") {
                        worker_cmd.env("PATH", format!("{};{}", python_bin_dir_worker, existing_path));
                    }
                }

                worker_cmd.args(["bootstrap_worker.py"]);

                match spawn_and_log(worker_cmd, "Python-Worker") {
                    Ok(child) => Some(child),
                    Err(e) => {
                        eprintln!("[Tauri] Falha ao iniciar Python-Worker: {}", e);
                        None
                    }
                }
            });

            // Aguarda todas as threads finalizarem e coleta os resultados
            let mut processes = state.lock().unwrap();
            processes.api = api_handle.join().unwrap_or(None);
            processes.node = node_handle.join().unwrap_or(None);
            processes.worker = worker_handle.join().unwrap_or(None);

            println!("[Tauri] Todos os backends iniciados em {:?}", startup_time.elapsed());

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<Mutex<BackendProcess>>();
                let mut processes = state.lock().unwrap();
                processes.kill_all();
            }
        })
        .run(tauri::generate_context!())
        .expect("erro ao rodar o tauri");
}
