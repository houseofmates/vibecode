.PHONY: help install run dev test clean build package appimage apk all update

help:
	@echo "VibeCode - Make targets"
	@echo ""
	@echo "Development:"
	@echo "  install   Install package in editable mode"
	@echo "  run      Run the server (http://192.168.4.233:8786)"
	@echo "  dev      Run in development with auto-reload"
	@echo "  test     Run tests"
	@echo "  clean    Clean build artifacts"
	@echo ""
	@echo "Packaging:"
	@echo "  build     Build Python wheel"
	@echo "  appimage  Build Linux AppImage → releases/vibecode.appimage"
	@echo "  apk       Build Android APK → releases/vibecode.apk"
	@echo "  all       Build all packages (AppImage + APK)"
	@echo ""
	@echo "Maintenance:"
	@echo "  check-appdir  Verify AppDir structure"
	@echo "  update        Check for VibeCode updates"

install:
	pip install -e .

run:
	python server.py

dev:
	@echo "Watching for changes..."
	@which inotifywait >/dev/null 2>&1 && inotifywait -r -e modify -q api/ static/ . || \
		echo "Install inotify-tools for auto-reload, falling back to manual run"
	python server.py

test:
	pytest -v || python -m pytest -v

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf __pycache__ api/__pycache__ static/__pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build:
	python -m build

package: appimage

appimage:
	@echo "Building VibeCode AppImage..."
	@./build-appimage.sh

apk:
	@echo "Building VibeCode APK..."
	@./build-apk.sh

all:
	@echo "Building all VibeCode packages..."
	@./build-all.sh

update:
	@echo "Checking for VibeCode updates..."
	@./check-update.sh

check-appdir:
	@echo "Checking AppDir structure..."
	@test -d AppDir || (echo "Creating AppDir..." && mkdir -p AppDir/usr/bin AppDir/usr/share/applications)
	@test -f AppDir/AppRun || (echo "WARNING: AppDir/AppRun missing!" && exit 1)
	@test -f AppDir/usr/share/applications/hermes-webui.desktop || (echo "WARNING: .desktop file missing!" && exit 1)
	@echo "AppDir structure OK"