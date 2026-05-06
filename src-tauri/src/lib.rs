use tauri::Manager;

#[cfg(target_os = "linux")]
use webkit2gtk::{WebContextExt, WebViewExt};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      #[cfg(target_os = "linux")]
      {
        for (_label, window) in app.webview_windows() {
          let _ = window.with_webview(|webview| {
            let wv = webview.inner();
            if let Some(context) = wv.web_context() {
              // Disable GTK system scrollbar theming so CSS ::-webkit-scrollbar
              // styles are respected instead of native black GTK scrollbars.
              context.set_use_system_appearance_for_scrollbars(false);
            }
          });
        }
      }

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri app");
}
