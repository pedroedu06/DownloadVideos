// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::process::{Command, Child};
use std::sync::Mutex;
use tauri::{Manager, WindowEvent};
use std::path::PathBuf;

struct BackendProcess {
    api: Option<Child>,
    worker: Option<Child>,
    node: Option<Child>,
}

fn main() {
        let exe_dir = std::env::current_exe()
            .expect("exe")
            .parent()
            .expect("parent")
            .to_path_buf();

        let python_dir = exe_dir
            .join("../../../backend/pythonservice")
            .canonicalize()
            .expect("nao foi possivel achar o pythonservice");

        let node_dir = exe_dir
            .join("../../../backend/node_service")
            .canonicalize()
            .expect("nao foi possivel achar o nodeservice");

        println!("{:?}",  python_dir);
        println!("{:?}", node_dir);
    
    
    tauri::Builder::default()

        .manage(Mutex::new(BackendProcess {
            api: None,
            worker: None,
            node: None
        }))
        .setup(move |app| {
            let state = app.state::<Mutex<BackendProcess>>();
            let mut processes = state.lock().unwrap();

            let api = Command::new("python")
                .current_dir(&python_dir)
                .args([
                    "-m", "uvicorn",
                    "api.main:app",
                    "--reload", "--host", "127.0.0.1",
                    "--port", "8000"
                ])
                .spawn()
                .expect("erro ao iniciar o uvicorn");

            let node = Command::new("node")
                .current_dir(&node_dir)
                .args([
                    "ts-node", "server.ts"
                ])
                .spawn()
                .expect("erro ao iniciar o ts-node");
        
            let worker = Command::new("python")
                .current_dir(&python_dir)
                .args([
                    "-m", "worker.worker"
                ])
                .spawn()
                .expect("erro ao iniciar o worker");

        processes.api = Some(api);
        processes.worker = Some(worker);
        processes.node = Some(node);
        
        Ok(())
    })
    .on_window_event(|window, event| {
        if let WindowEvent::CloseRequested { .. } = event {
            let app = window.app_handle();
            let state = app.state::<Mutex<BackendProcess>>();
            let mut processes = state.lock().unwrap();

            if let Some(mut api) = processes.api.take(){
                let _ = api.kill();
            }

            if let Some(mut worker) = processes.worker.take() {
                let _ = worker.kill();
            }

            if let Some(mut node) = processes.node.take() {
                let _ = node.kill();
            }
        }
    })

    .run(tauri::generate_context!())
    .expect("erro ao rodar o tauri")     
}
