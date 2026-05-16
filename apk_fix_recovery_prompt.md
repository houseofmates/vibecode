# APK Fix Recovery Prompt
## Send this to Claude Sonnet 4.6 if the APK still has issues

---

You are working on the "hermes webui" / vibecode Android APK. The app is a plain HTML/CSS/JS web app packaged via Capacitor. Static files live in `static/`, built to `dist/` via `./build-tauri-dist.sh`, then synced to `android/app/src/main/assets/public/` via `npx cap sync android`. Run `./build-apk.sh` to build the full APK and copy it to `releases/vibecode.apk`.

## Architecture facts

- **APK detection**: `window.Capacitor` or `location.protocol === 'capacitor:'` or `html.classList.contains('capacitor')`  
- **APK CSS class**: `html.apk-force-mobile` is added to `<html>` in a `<head>` script when Capacitor is detected
- **Sidebar structure**: All `.panel-view` elements are **inside** `<aside class="sidebar">` in the DOM
- **Critical CSS quirk**: Any element with `transform` on it creates a containing block for `position:fixed` children. The sidebar has `transform: translateX(-100%)` by default, which means `position:fixed` panel-views inside it position relative to the sidebar (off-screen), NOT the viewport
- **The sidebar hiding fix**: In `static/mobile.css`, at the very end (APK FINAL FIXES section), the sidebar is hidden via `left: -100vw !important; transform: none !important` instead of `transform: translateX(-100%)`. This is CRITICAL — removing transform means panel-view children with `position:fixed` correctly anchor to the viewport
- **Panels**: `switchMobilePanel(name)` in `static/panels.js` handles panel switching. It adds `active` class to the target `.panel-view` and removes it from others
- **Nav bar**: `#mobileBottomNav` is a `<nav>` at the end of `<body>` (NOT inside sidebar). Has 5 buttons: chat, tasks, skills, workspaces (files), terminal — each calls `switchMobilePanel(name)`
- **Topbar buttons**: `#btnWorkspacePanelToggle` (class `chip workspace-toggle-btn`) and `#btnTerminalPanelToggle` (class `chip terminal-toggle-btn`) — in APK mode, their `onclick` is rewritten to `switchMobilePanel('workspaces')` and `switchMobilePanel('terminal')` in `applyApkHardOverrides()` in `static/index.html`
- **30px top inset**: Comes from `html.apk-force-mobile .layout { padding-top: 30px !important }` in mobile.css (NOT from body padding)

## Current known issues to fix (if still broken)

### Issue A: Pressing file/terminal topbar button opens blank screen
**Root cause**: The `.sidebar` element has `transform: translateX(-100%)` applied (from earlier CSS rules). This creates a new CSS containing block, making `position:fixed` children of the sidebar position relative to the off-screen sidebar instead of the viewport.

**Fix**: In `static/mobile.css`, append at the very end (after all other rules):
```css
html.apk-force-mobile .sidebar {
  transform: none !important;
  left: -100vw !important;
}
html.apk-force-mobile .sidebar.mobile-open {
  left: 0 !important;
  transform: none !important;
}
```
This changes sidebar hiding from transform-based to left-position-based, removing the containing block problem.

### Issue B: No bottom nav bar buttons visible
**Root cause**: Could be (a) CSS hiding nav items, (b) icon color blending with background, or (c) z-index/stacking issue from panel-views.

**Fix**: Append to `static/mobile.css`:
```css
html.apk-force-mobile .mobile-nav-item {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
  color: #d7dde7 !important;
}
html.apk-force-mobile .mobile-nav-item.active {
  color: #35c7ff !important;
}
html.apk-force-mobile .mobile-nav-item svg {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
  fill: none !important;
  stroke: currentColor !important;
}
```

Also verify in `applyApkHardOverrides()` in `static/index.html` that the nav element `#mobileBottomNav` gets:
```js
nav.style.setProperty('display', 'flex', 'important');
nav.style.zIndex = '2147483647';
nav.style.position = 'fixed';
nav.style.bottom = '0';
nav.style.left = '0';
nav.style.right = '0';
nav.style.height = '72px';
```

### Issue C: File/workspace topbar button highlights with sharp corners
**Root cause**: Android WebView's `-webkit-appearance: button` can override `border-radius`. The `.chip { border-radius: 999px }` CSS rule isn't always respected.

**Fix 1 (CSS)**: Append to `static/mobile.css`:
```css
.workspace-toggle-btn.active {
  border-radius: 999px !important;
}
.terminal-toggle-btn.active {
  color: var(--blue) !important;
  border-color: rgba(124, 185, 255, .35) !important;
  background: rgba(124, 185, 255, .1) !important;
  border-radius: 999px !important;
}
```

**Fix 2 (JS — most reliable)**: In `switchMobilePanel()` in `static/panels.js`, when toggling active on topbar buttons:
```js
if(wt) {
  wt.classList.toggle('active', name === 'workspaces');
  wt.style.setProperty('border-radius', '999px', 'important');
  wt.style.setProperty('-webkit-appearance', 'none', 'important');
}
if(tt) {
  tt.classList.toggle('active', name === 'terminal');
  tt.style.setProperty('border-radius', '999px', 'important');
  tt.style.setProperty('-webkit-appearance', 'none', 'important');
}
```

Also apply in `applyApkHardOverrides()` at initial setup:
```js
workspaceToggle.style.setProperty('border-radius', '999px', 'important');
workspaceToggle.style.setProperty('-webkit-appearance', 'none', 'important');
terminalToggle.style.setProperty('border-radius', '999px', 'important');
terminalToggle.style.setProperty('-webkit-appearance', 'none', 'important');
```

### Issue D: Terminal button not highlighted when active
**Root cause**: No `.terminal-toggle-btn.active` CSS rule existed in the original codebase. The CSS for active state was missing for this button.

**Fix**: The CSS rule in Issue C Fix 1 covers this. Additionally in `switchMobilePanel`, the `tt.classList.toggle('active', name === 'terminal')` handles the class toggling.

## CSS cascade rules to keep in mind

1. `!important` inline style (`el.style.setProperty('prop','val','important')`) beats ALL stylesheet rules
2. Among `!important` stylesheet rules, higher specificity wins
3. Among equal specificity `!important` rules, the LATER one in the file wins
4. `transform` on a parent element creates a new containing block for `position:fixed` children — this is the #1 most surprising bug in this codebase
5. Always append APK fixes to the END of `mobile.css` to guarantee highest priority

## Build & test workflow

```bash
# Quick rebuild (no full Gradle):
./build-tauri-dist.sh && npx cap sync android

# Full APK rebuild:
./build-apk.sh

# Verify a fix is in the packaged assets:
grep "your-pattern" android/app/src/main/assets/public/static/mobile.css

# APK output:
ls -la releases/vibecode.apk
```

## Files to edit

- `static/mobile.css` — APK CSS (append new rules at END for highest priority)
- `static/index.html` — `applyApkHardOverrides()` function (around line 192)  
- `static/panels.js` — `switchMobilePanel()` function (around line 3179)

## DO NOT touch

- `static/style.css` layout rules (especially `.layout { flex-direction }`) — website layout depends on it
- `static/boot.js` `toggleWorkspacePanel()` — used by the website; APK overrides via onclick attribute
- Any server-side Python files

## Requirements summary

1. APK shows working bottom nav bar with 5 icon-only buttons (chat, tasks, skills, files, terminal)
2. Nav buttons switch/open the correct full-screen panel overlays
3. APK has exactly 30px top status bar padding
4. No blue separator bar above bottom nav
5. Files button is to the LEFT of terminal button in topbar chips
6. Normal website at http://127.0.0.1:8786/ must still render correctly
7. Rebuilt APK is at `releases/vibecode.apk`
