// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            // Set zoom factor to 1.2 (120%) and re-apply on page load
            window.eval(r#"
                (function() {
                    const applyZoom = () => {
                        document.body.style.zoom = '1.2';
                    };
                    applyZoom();
                    window.addEventListener('load', applyZoom);
                    window.addEventListener('DOMContentLoaded', applyZoom);
                })();
            "#).ok();
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
