// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{path::BaseDirectory, Manager, WindowEvent};
use std::io::{BufRead, BufReader};
use std::thread;

struct BackendProcess {
    api: Option<Child>,
    worker: Option<Child>,
    node: Option<Child>,
}

impl BackendProcess {
    fn kill_all(&mut self) {
        println!("[Tauri] Encerrando todos os processos de backend...");
        if let Some(mut child) = self.api.take() {
            let _ = child.kill();
        }
        if let Some(mut child) = self.worker.take() {
            let _ = child.kill();
        }
        if let Some(mut child) = self.node.take() {
            let _ = child.kill();
        }
    }
}

fn spawn_and_log(mut command: Command, name: &'static str) -> std::io::Result<Child> {
    // Redireciona stdout e stderr para que possamos ver o que acontece no backend
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());

    let mut child = command.spawn()?;
    
    let stdout = child.stdout.take().unwrap();
    let stderr = child.stderr.take().unwrap();

    // Thread para logar o stdout
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(l) = line {
                println!("[{}] {}", name, l);
            }
        }
    });

    // Thread para logar o stderr
    thread::spawn(move || {
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            if let Ok(l) = line {
                eprintln!("[{} ERROR] {}", name, l);
            }
        }
    });

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
            let handle = app.handle();
            let state = handle.state::<Mutex<BackendProcess>>();

            // 1. Tratar paths de forma robusta
            let (python_dir, node_dir) = if cfg!(debug_assertions) {
                let mut base = std::env::current_dir().unwrap();
                if base.ends_with("src-tauri") {
                    base = base.parent().unwrap().to_path_buf();
                }
                (base.join("backend/pythonservice"), base.join("backend/node_service"))
            } else {
                (
                    app.path().resolve("backend/pythonservice", BaseDirectory::Resource).expect("Erro Python Path"),
                    app.path().resolve("backend/node_service", BaseDirectory::Resource).expect("Erro Node Path")
                )
            };

            println!("[Tauri] Python Dir: {:?}", python_dir);
            println!("[Tauri] Node Dir: {:?}", node_dir);

            // 2. Definir binários
            let python_bin = if cfg!(debug_assertions) {
                "python".to_string()
            } else {
                app.path()
                    .resolve("backend/bin/python/python.exe", BaseDirectory::Resource)
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_else(|_| "python".to_string())
            };

            let node_bin = if cfg!(debug_assertions) {
                "node".to_string()
            } else {
                app.path()
                    .resolve("backend/bin/node/node.exe", BaseDirectory::Resource)
                    .map(|p| p.to_string_lossy().to_string())
                    .unwrap_or_else(|_| "node".to_string())
            };

            // 3. Execução dos Processos com Logs
            let mut processes = state.lock().unwrap();

            // API Python
            if !python_dir.exists() {
                eprintln!("[Tauri] Erro: Diretório da API Python não encontrado em {:?}", python_dir);
            } else {
                let mut api_args = vec!["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"];
                if cfg!(debug_assertions) {
                    api_args.push("--reload");
                }

                let mut cmd = Command::new(&python_bin);
                cmd.current_dir(&python_dir).args(&api_args);
                
                match spawn_and_log(cmd, "Python-API") {
                    Ok(child) => processes.api = Some(child),
                    Err(e) => eprintln!("[Tauri] Falha ao iniciar Python-API: {}", e),
                }
            }

            // Node Service
            if !node_dir.exists() {
                eprintln!("[Tauri] Erro: Diretório do Node Service não encontrado em {:?}", node_dir);
            } else {
                let mut node_cmd = if cfg!(debug_assertions) {
                    let mut cmd = Command::new("cmd");
                    cmd.current_dir(&node_dir).args(["/c", "npx", "ts-node", "server.ts"]);
                    cmd
                } else {
                    let mut cmd = Command::new(&node_bin);
                    cmd.current_dir(&node_dir).args(["dist/server.js"]);
                    cmd
                };

                match spawn_and_log(node_cmd, "Node-Service") {
                    Ok(child) => processes.node = Some(child),
                    Err(e) => eprintln!("[Tauri] Falha ao iniciar Node-Service: {}", e),
                }
            }

            // Worker Python
            if python_dir.exists() {
                let mut worker_cmd = Command::new(&python_bin);
                worker_cmd.current_dir(&python_dir).args(["-m", "worker.worker"]);
                
                match spawn_and_log(worker_cmd, "Python-Worker") {
                    Ok(child) => processes.worker = Some(child),
                    Err(e) => eprintln!("[Tauri] Falha ao iniciar Python-Worker: {}", e),
                }
            }

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

