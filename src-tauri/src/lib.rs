use tauri::Manager;

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
        if let Some(window) = app.get_webview_window("main") {
          let _ = window.with_webview(|webview| {
            use webkit2gtk::WebViewExt;
            use webkit2gtk::SettingsExt;
            let wv: webkit2gtk::WebView = webview.inner();
            if let Some(settings) = WebViewExt::settings(&wv) {
              settings.set_disable_web_security(true);
              settings.set_enable_developer_extras(true);
              println!("[tauri] Disabled web security and enabled devtools");
            }
            // Zoom in 1.2x for better readability on desktop
            wv.set_zoom_level(1.2);
            println!("[tauri] Set zoom level to 1.2");
          });

          // Inject GTK CSS to force scrollbar styling in WebKit2GTK
          // (GTK themes often override ::-webkit-scrollbar web CSS)
          use gtk::CssProvider;
          use gtk::StyleContext;
          use gtk::prelude::CssProviderExt;
          if let Some(screen) = gdk::Screen::default() {
            let provider = CssProvider::new();
            let css = r#"
              scrollbar {
                background: transparent;
              }
              scrollbar slider {
                background: #f6b012;
                border-radius: 3px;
                min-width: 6px;
                min-height: 6px;
              }
              scrollbar trough {
                background: transparent;
              }
            "#;
            if provider.load_from_data(css.as_bytes()).is_ok() {
              StyleContext::add_provider_for_screen(
                &screen,
                &provider,
                gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
              );
              println!("[tauri] Injected GTK scrollbar CSS");
            }
          }
        }
      }

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
