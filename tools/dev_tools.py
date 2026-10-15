# SPDX-FileCopyrightText: Copyright (c) 2026 CADIT. All rights reserved.
"""
Omniverse Modular Project Scaffolding Engine.
Provides commands for:
  - init: Injects Core Architecture, Four Helpers, and Level 1 Starter (with idempotency guard)
  - add: Scaffolds a new level from standard template
  - list: Inspects and displays all registered levels in the extension
"""

import os
import sys
import re
import argparse
from pathlib import Path


def get_workspace_root() -> Path:
    """
    Returns the workspace root directory containing source/extensions.
    Supports running directly at root, or from inside a subfolder like cadit-omniverse-helper/.
    """
    tools_dir = Path(__file__).resolve().parent
    helper_dir = tools_dir.parent  # e.g. .../cadit-omniverse-helper or .../my-project

    # Check 1: Is helper_dir itself the workspace root?
    if (helper_dir / "source" / "extensions").is_dir():
        return helper_dir

    # Check 2: Is helper_dir's parent the workspace root? (subfolder scenario)
    if (helper_dir.parent / "source" / "extensions").is_dir():
        return helper_dir.parent

    # Check 3: Walk upwards looking for source/extensions or repo.bat
    curr = helper_dir.parent
    while curr.parent != curr:
        if (curr / "source" / "extensions").is_dir() or (curr / "repo.bat").is_file():
            return curr
        curr = curr.parent

    # Fallback to helper_dir
    return helper_dir


def get_templates_dir() -> Path:
    """Returns the tools/templates directory."""
    return Path(__file__).resolve().parent / "templates"


def get_available_extensions(ws: Path) -> list:
    """Returns list of valid extension directory names inside source/extensions."""
    ext_base = ws / "source" / "extensions"
    if not ext_base.is_dir():
        return []
    return sorted([
        p.name for p in ext_base.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ])


def resolve_extension_paths(ext_name: str = None, require_explicit: bool = False) -> tuple:
    """
    Resolves (ext_name, ext_root_dir, pkg_dir).
    Requires explicit extension name or resolves single detected extension.
    """
    ws = get_workspace_root()
    extensions_base = ws / "source" / "extensions"

    if not extensions_base.is_dir():
        print(f"[ERROR] Direktori 'source/extensions' tidak ditemukan di workspace: {ws}")
        sys.exit(1)

    available = get_available_extensions(ws)

    # If extension name is not provided
    if not ext_name:
        if not available:
            print(f"[ERROR] Tidak ada folder ekstensi ditemukan di: {extensions_base}")
            print("Harap buat ekstensi terlebih dahulu (contoh: .\\repo.bat template new)")
            sys.exit(1)

        if require_explicit or len(available) > 1:
            print("[ERROR] Harap tentukan nama ekstensi target!")
            print(f"Daftar ekstensi yang terdeteksi di {extensions_base}:")
            for idx, name in enumerate(available, 1):
                print(f"  {idx}. {name}")
            print("\nContoh penggunaan:")
            print(f"  .\\init_framework.bat {available[0]}")
            sys.exit(1)
        else:
            ext_name = available[0]
            print(f"[INFO] Menggunakan ekstensi tunggal yang terdeteksi: '{ext_name}'")

    ext_root = extensions_base / ext_name
    if not ext_root.is_dir():
        print(f"[ERROR] Ekstensi '{ext_name}' tidak ditemukan di: {extensions_base}")
        if available:
            print("Daftar ekstensi yang tersedia di proyek ini:")
            for idx, name in enumerate(available, 1):
                print(f"  {idx}. {name}")
        sys.exit(1)

    parts = ext_name.split(".")
    pkg_dir = ext_root.joinpath(*parts)

    if not pkg_dir.is_dir():
        for p in ext_root.rglob("__init__.py"):
            pkg_dir = p.parent
            break

    return ext_name, ext_root, pkg_dir


def to_pascal_case(snake_str: str) -> str:
    """Converts 'my_company.modular_project' to 'MyCompanyModularProject'."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", snake_str)
    return "".join(part.capitalize() for part in clean.split("_") if part)


def read_template(template_name: str) -> str:
    """Reads a template file from tools/templates."""
    t_path = get_templates_dir() / template_name
    if not t_path.is_file():
        print(f"[ERROR] Template file missing: {t_path}")
        sys.exit(1)
    with open(t_path, "r", encoding="utf-8") as f:
        return f.read()


def ensure_root_integration(ws: Path, helper_dir: Path) -> None:
    """
    If running from a subfolder (e.g. cadit-omniverse-helper/),
    automatically injects to root .gitignore and exports root shortcuts.
    """
    if ws == helper_dir:
        return

    subfolder_name = helper_dir.name
    pattern = f"{subfolder_name}/"

    # 1. Inject to root .gitignore
    gitignore_path = ws / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if subfolder_name not in content:
            with open(gitignore_path, "a", encoding="utf-8") as f:
                f.write(f"\n# CADIT Omniverse Helper Toolkit\n{pattern}\n")
            print(f"  [+] Injected '{pattern}' into root .gitignore (eliminating nested git)")
    else:
        gitignore_path.write_text(f"# CADIT Omniverse Helper Toolkit\n{pattern}\n", encoding="utf-8")
        print(f"  [+] Created root .gitignore with '{pattern}'")

    # 2. Export universal root shortcuts
    root_add_bat = ws / "add.bat"
    root_list_bat = ws / "list_levels.bat"
    root_init_bat = ws / "init_framework.bat"

    init_cmd = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set SCRIPT_DIR=%~dp0\r\n"
        'if "%~1"=="" (\r\n'
        "    echo [ERROR] Harap tentukan nama ekstensi target yang ingin diinisialisasi!\r\n"
        "    echo Contoh penggunaan:\r\n"
        "    echo   .\\init_framework.bat company.my_extension\r\n"
        "    echo.\r\n"
        ")\r\n"
        f'if exist "%SCRIPT_DIR%{subfolder_name}\\tools\\dev_tools.py" (\r\n'
        f'    python "%SCRIPT_DIR%{subfolder_name}\\tools\\dev_tools.py" init %*\r\n'
        ") else (\r\n"
        '    python "%SCRIPT_DIR%tools\\dev_tools.py" init %*\r\n'
        ")\r\n"
        "endlocal\r\n"
    )
    add_cmd = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set SCRIPT_DIR=%~dp0\r\n"
        'if "%~1"=="" (\r\n'
        "    echo [ERROR] Harap tentukan nama level yang ingin dibuat!\r\n"
        "    echo Contoh penggunaan:\r\n"
        "    echo   .\\add.bat level_02_room\r\n"
        "    echo   .\\add.bat level_2_chiller [nama_ekstensi]\r\n"
        "    exit /b 1\r\n"
        ")\r\n"
        f'if exist "%SCRIPT_DIR%{subfolder_name}\\tools\\dev_tools.py" (\r\n'
        f'    python "%SCRIPT_DIR%{subfolder_name}\\tools\\dev_tools.py" add %*\r\n'
        ") else (\r\n"
        '    python "%SCRIPT_DIR%tools\\dev_tools.py" add %*\r\n'
        ")\r\n"
        "endlocal\r\n"
    )
    list_cmd = (
        "@echo off\r\n"
        "setlocal\r\n"
        "set SCRIPT_DIR=%~dp0\r\n"
        f'if exist "%SCRIPT_DIR%{subfolder_name}\\tools\\dev_tools.py" (\r\n'
        f'    python "%SCRIPT_DIR%{subfolder_name}\\tools\\dev_tools.py" list %*\r\n'
        ") else (\r\n"
        '    python "%SCRIPT_DIR%tools\\dev_tools.py" list %*\r\n'
        ")\r\n"
        "endlocal\r\n"
    )
    init_sh_cmd = (
        "#!/usr/bin/env bash\n"
        'SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"\n'
        'if [ -z "$1" ]; then\n'
        '    echo "[ERROR] Harap tentukan nama ekstensi target yang ingin diinisialisasi!"\n'
        '    echo\n'
        '    echo "Contoh penggunaan:"\n'
        '    echo "  ./init_framework.sh company.my_extension"\n'
        '    echo\n'
        'fi\n'
        f'if [ -f "$SCRIPT_DIR/{subfolder_name}/tools/dev_tools.py" ]; then\n'
        f'    python "$SCRIPT_DIR/{subfolder_name}/tools/dev_tools.py" init "$@"\n'
        "else\n"
        '    python "$SCRIPT_DIR/tools/dev_tools.py" init "$@"\n'
        "fi\n"
    )
    add_sh_cmd = (
        "#!/usr/bin/env bash\n"
        'SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"\n'
        'if [ -z "$1" ]; then\n'
        '    echo "[ERROR] Harap tentukan nama level yang ingin dibuat!"\n'
        '    echo "Contoh penggunaan:"\n'
        '    echo "  ./add.sh level_02_room"\n'
        '    echo "  ./add.sh level_2_chiller [nama_ekstensi]"\n'
        '    exit 1\n'
        'fi\n'
        f'if [ -f "$SCRIPT_DIR/{subfolder_name}/tools/dev_tools.py" ]; then\n'
        f'    python "$SCRIPT_DIR/{subfolder_name}/tools/dev_tools.py" add "$@"\n'
        "else\n"
        '    python "$SCRIPT_DIR/tools/dev_tools.py" add "$@"\n'
        "fi\n"
    )
    list_sh_cmd = (
        "#!/usr/bin/env bash\n"
        'SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"\n'
        f'if [ -f "$SCRIPT_DIR/{subfolder_name}/tools/dev_tools.py" ]; then\n'
        f'    python "$SCRIPT_DIR/{subfolder_name}/tools/dev_tools.py" list "$@"\n'
        "else\n"
        '    python "$SCRIPT_DIR/tools/dev_tools.py" list "$@"\n'
        "fi\n"
    )

    launch_cmd = (
        "@echo off\r\n"
        "setlocal\r\n"
        "echo ======================================================================\r\n"
        "echo   Launching Omniverse Web View Streaming Application...\r\n"
        "echo   Target: cadit.web_view_only.kit ^| Signaling Port: 49100\r\n"
        "echo ======================================================================\r\n"
        "call .\\repo.bat launch -n cadit.web_view_only.kit %*\r\n"
        "endlocal\r\n"
    )
    launch_sh_cmd = (
        "#!/usr/bin/env bash\n"
        'echo "======================================================================"\n'
        'echo "  Launching Omniverse Web View Streaming Application..."\n'
        'echo "  Target: cadit.web_view_only.kit | Signaling Port: 49100"\n'
        'echo "======================================================================"\n'
        './repo.sh launch -n cadit.web_view_only.kit "$@"\n'
    )

    root_init_sh = ws / "init_framework.sh"
    root_add_sh = ws / "add.sh"
    root_list_sh = ws / "list_levels.sh"
    root_launch_bat = ws / "launch_web_view.bat"
    root_launch_sh = ws / "launch_web_view.sh"

    created_shortcuts = []
    if not root_init_bat.exists():
        root_init_bat.write_text(init_cmd, encoding="utf-8")
        created_shortcuts.append("init_framework.bat")
    if not root_add_bat.exists():
        root_add_bat.write_text(add_cmd, encoding="utf-8")
        created_shortcuts.append("add.bat")
    if not root_list_bat.exists():
        root_list_bat.write_text(list_cmd, encoding="utf-8")
        created_shortcuts.append("list_levels.bat")
    if not root_launch_bat.exists():
        root_launch_bat.write_text(launch_cmd, encoding="utf-8")
        created_shortcuts.append("launch_web_view.bat")

    if not root_init_sh.exists():
        root_init_sh.write_text(init_sh_cmd, encoding="utf-8")
        created_shortcuts.append("init_framework.sh")
    if not root_add_sh.exists():
        root_add_sh.write_text(add_sh_cmd, encoding="utf-8")
        created_shortcuts.append("add.sh")
    if not root_list_sh.exists():
        root_list_sh.write_text(list_sh_cmd, encoding="utf-8")
        created_shortcuts.append("list_levels.sh")
    if not root_launch_sh.exists():
        root_launch_sh.write_text(launch_sh_cmd, encoding="utf-8")
        created_shortcuts.append("launch_web_view.sh")

    if created_shortcuts:
        print(f"  [+] Exported root shortcuts: {', '.join(created_shortcuts)} to project root")


def ensure_web_view_app(ws: Path, ext_name: str, force: bool = False) -> None:
    """
    Scaffolds dedicated Web View Kit app (source/apps/cadit.web_view_only.kit),
    registers it in premake5.lua and repo.toml, and ensures streaming bundles.
    """
    apps_dir = ws / "source" / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    web_view_kit = apps_dir / "cadit.web_view_only.kit"

    template_file = get_templates_dir() / "web_view_app_template.kit.txt"
    if not template_file.exists():
        print(f"[ERROR] Template '{template_file.name}' tidak ditemukan.")
        return

    # 1. Generate cadit.web_view_only.kit if missing or forced
    if not web_view_kit.exists() or force:
        title = f"Web View {ext_name.split('.')[-1].replace('_', ' ').title()}"
        content = template_file.read_text(encoding="utf-8")
        content = content.replace("{{package_title}}", title)
        content = content.replace("{{extension_name}}", ext_name)

        # Detect if project uses Pixar Hydra (omni.hydra.pxr) instead of RTX (omni.hydra.rtx)
        uses_pxr = False
        for kit_file in apps_dir.glob("*.kit"):
            if kit_file.name != "cadit.web_view_only.kit":
                kit_text = kit_file.read_text(encoding="utf-8", errors="ignore")
                if '"omni.hydra.pxr"' in kit_text and '"omni.hydra.rtx"' not in kit_text:
                    uses_pxr = True
                    break

        if uses_pxr:
            content = content.replace('"omni.hydra.rtx" = {}', '"omni.hydra.pxr" = {}')
            content = content.replace('"omni.rtx.settings.core" = {}', '#"omni.rtx.settings.core" = {}')
            content = content.replace('exts."omni.rtx.window.settings".window_menu', '#exts."omni.rtx.window.settings".window_menu')
            content = content.replace('rtx.sceneDb.ambientLightIntensity', '#rtx.sceneDb.ambientLightIntensity')
            content = content.replace('rtx.ecoMode.enabled', '#rtx.ecoMode.enabled')
            content = content.replace('rtx.hydra.mdlMaterialWarmup', '#rtx.hydra.mdlMaterialWarmup')

        web_view_kit.write_text(content, encoding="utf-8")
        print(f"  [+] Created dedicated streaming app: source/apps/{web_view_kit.name}")
    else:
        print(f"  [INFO] Streaming app 'source/apps/{web_view_kit.name}' sudah aktif.")

    # 2. Register in premake5.lua
    premake_file = ws / "premake5.lua"
    if premake_file.exists():
        premake_content = premake_file.read_text(encoding="utf-8")
        if 'define_app("cadit.web_view_only.kit")' not in premake_content:
            premake_content = premake_content.rstrip() + '\ndefine_app("cadit.web_view_only.kit")\n'
            premake_file.write_text(premake_content, encoding="utf-8")
            print("  [+] Registered cadit.web_view_only.kit in premake5.lua")

    # 3. Register in repo.toml under repo_precache_exts.apps
    repo_file = ws / "repo.toml"
    if repo_file.exists():
        repo_content = repo_file.read_text(encoding="utf-8")
        if "cadit.web_view_only.kit" not in repo_content:
            def _add_app(match):
                curr_apps = match.group(0)
                if '"${root}/source/apps/cadit.web_view_only.kit"' not in curr_apps:
                    closing_idx = curr_apps.rfind("]")
                    if closing_idx != -1:
                        prefix = curr_apps[:closing_idx].rstrip()
                        if prefix.endswith("["):
                            return f'{prefix}"${{root}}/source/apps/cadit.web_view_only.kit"]'
                        else:
                            return f'{prefix}, "${{root}}/source/apps/cadit.web_view_only.kit"]'
                return curr_apps

            repo_content = re.sub(r'apps\s*=\s*\[[^\]]*\]', _add_app, repo_content, count=1)
            repo_file.write_text(repo_content, encoding="utf-8")
            print("  [+] Registered cadit.web_view_only.kit in repo.toml")

    # 4. Generate root launcher shortcuts
    root_launch_bat = ws / "launch_web_view.bat"
    root_launch_sh = ws / "launch_web_view.sh"

    launch_bat_content = (
        "@echo off\r\n"
        "setlocal\r\n"
        "echo ======================================================================\r\n"
        "echo   Launching Omniverse Web View Streaming Application...\r\n"
        "echo   Target: cadit.web_view_only.kit ^| Signaling Port: 49100\r\n"
        "echo ======================================================================\r\n"
        "call .\\repo.bat launch -n cadit.web_view_only.kit %*\r\n"
        "endlocal\r\n"
    )
    launch_sh_content = (
        "#!/usr/bin/env bash\n"
        'echo "======================================================================"\n'
        'echo "  Launching Omniverse Web View Streaming Application..."\n'
        'echo "  Target: cadit.web_view_only.kit | Signaling Port: 49100"\n'
        'echo "======================================================================"\n'
        './repo.sh launch -n cadit.web_view_only.kit "$@"\n'
    )

    if not root_launch_bat.exists() or force:
        root_launch_bat.write_text(launch_bat_content, encoding="utf-8")
        print("  [+] Created root launcher shortcut: launch_web_view.bat")

    if not root_launch_sh.exists() or force:
        root_launch_sh.write_text(launch_sh_content, encoding="utf-8")
        print("  [+] Created root launcher shortcut: launch_web_view.sh")

    # 5. Sync streaming extension bundles if available in extscache
    dest_extscache = ws / "_build" / "windows-x86_64" / "release" / "extscache"
    if dest_extscache.is_dir():
        livestream_found = list(dest_extscache.glob("*omni.kit.livestream.app*"))
        if not livestream_found and ws.parent.is_dir():
            import shutil
            for sibling in ["data-centre", "complete-data-centre"]:
                src_cache = ws.parent / sibling / "_build" / "windows-x86_64" / "release" / "extscache"
                if src_cache.is_dir():
                    for item in src_cache.glob("*livestream*"):
                        target_dir = dest_extscache / item.name
                        if not target_dir.exists():
                            try:
                                shutil.copytree(item, target_dir)
                                print(f"  [+] Copied cached extension: {item.name}")
                            except Exception:
                                pass
                    break


def cmd_init(args):
    """Initializes extension with Core, Four Helpers, and Starter Level 1."""
    ws = get_workspace_root()
    helper_dir = Path(__file__).resolve().parent.parent

    # Require explicit extension name if multiple exist or if user omitted
    ext_name, ext_root, pkg_dir = resolve_extension_paths(args.extension, require_explicit=True)
    manager_path = pkg_dir / "core" / "manager.py"

    print("=" * 70)
    print("  OMNIVERSE MODULAR FRAMEWORK - INITIALIZATION")
    print("=" * 70)
    print(f"[WORKSPACE] Root: {ws}")
    print(f"[TARGET]    Ekstensi target: '{ext_name}'")
    print(f"[PATH]      Package path: {pkg_dir}")

    # Ensure integration with root project if in subfolder
    ensure_root_integration(ws, helper_dir)

    # Idempotency safety guard
    if manager_path.exists() and not args.force:
        print()
        print(f"[WARNING] Ekstensi '{ext_name}' SUDAH terinisialisasi sebelumnya!")
        print(f"[INFO]    File '{manager_path.name}' telah aktif.")
        print("[INFO]    Seluruh file core dan level Anda tetap aman dan TIDAK ditimpa.")
        print("-" * 70)
        print("Tips Penggunaan:")
        print("  - Untuk menambah level baru, jalankan: .\\add.bat <nama_level>")
        print("  - Untuk melihat daftar level, jalankan: .\\list_levels.bat")
        print(f"  - Untuk memaksa reset total (HATI-HATI), gunakan: .\\init_framework.bat {ext_name} --force")
        print("-" * 70)
        return 0

    if args.force and manager_path.exists():
        print("[FORCE] Menimpa file core sesuai instruksi --force...")

    # 1. Directories setup
    core_dir = pkg_dir / "core"
    helpers_dir = core_dir / "helpers"
    levels_dir = pkg_dir / "levels"

    core_dir.mkdir(parents=True, exist_ok=True)
    helpers_dir.mkdir(parents=True, exist_ok=True)
    levels_dir.mkdir(parents=True, exist_ok=True)

    # 2. Write core/__init__.py
    (core_dir / "__init__.py").write_text("# Core architecture package\n", encoding="utf-8")

    # 3. Write core/context.py
    context_code = read_template("context_template.py.txt")
    (core_dir / "context.py").write_text(context_code, encoding="utf-8")
    print("  [+] Created core/context.py")

    # 4. Write core/helpers/__init__.py
    (helpers_dir / "__init__.py").write_text("# Core helpers package\n", encoding="utf-8")

    # 5. Write core/helpers/visibility_helper.py
    vis_code = read_template("visibility_helper_template.py.txt")
    (helpers_dir / "visibility_helper.py").write_text(vis_code, encoding="utf-8")
    print("  [+] Created core/helpers/visibility_helper.py")

    # 6. Write core/helpers/projection_helper.py
    proj_code = read_template("projection_helper_template.py.txt")
    (helpers_dir / "projection_helper.py").write_text(proj_code, encoding="utf-8")
    print("  [+] Created core/helpers/projection_helper.py")

    # 7. Write core/helpers/color_helper.py
    color_code = read_template("color_helper_template.py.txt")
    (helpers_dir / "color_helper.py").write_text(color_code, encoding="utf-8")
    print("  [+] Created core/helpers/color_helper.py")

    # 8. Write core/helpers/camera_helper.py
    cam_code = read_template("camera_helper_template.py.txt")
    (helpers_dir / "camera_helper.py").write_text(cam_code, encoding="utf-8")
    print("  [+] Created core/helpers/camera_helper.py")

    # 9. Write core/helpers/selection_helper.py
    sel_code = read_template("selection_helper_template.py.txt")
    (helpers_dir / "selection_helper.py").write_text(sel_code, encoding="utf-8")
    print("  [+] Created core/helpers/selection_helper.py")

    # 10. Write core/helpers/telemetry_helper.py
    telem_code = read_template("telemetry_helper_template.py.txt")
    (helpers_dir / "telemetry_helper.py").write_text(telem_code, encoding="utf-8")
    print("  [+] Created core/helpers/telemetry_helper.py")

    # 11. Write core/base_level.py
    base_level_code = read_template("base_level_template.py.txt")
    (core_dir / "base_level.py").write_text(base_level_code, encoding="utf-8")
    print("  [+] Created core/base_level.py")

    # 10. Write core/manager.py
    manager_code = read_template("manager_template.py.txt")
    (core_dir / "manager.py").write_text(manager_code, encoding="utf-8")
    print("  [+] Created core/manager.py")

    # 11. Write levels/__init__.py
    levels_init_path = levels_dir / "__init__.py"
    if not levels_init_path.exists() or args.force:
        levels_init_path.write_text("# Levels package\n", encoding="utf-8")
        print("  [+] Created levels/__init__.py")

    # 12. Write levels/level_01_default.py (Starter Level 1)
    starter_path = levels_dir / "level_01_default.py"
    if not starter_path.exists() or args.force:
        starter_code = read_template("level_starter_template.py.txt")
        starter_path.write_text(starter_code, encoding="utf-8")
        print("  [+] Created levels/level_01_default.py (Auto Starter Demo)")

    # 13. Update extension.py
    ext_py_path = pkg_dir / "extension.py"
    ext_code = read_template("extension_template.py.txt")
    ext_class_name = to_pascal_case(ext_name) + "Extension"
    ext_code = ext_code.replace("{package_name}", ext_name)
    ext_code = ext_code.replace("{ext_class_name}", ext_class_name)
    ext_py_path.write_text(ext_code, encoding="utf-8")
    print(f"  [+] Updated extension.py with class '{ext_class_name}'")

    # 14. Ensure dedicated Web View streaming app (cadit.web_view_only.kit)
    ensure_web_view_app(ws, ext_name, force=args.force)

    print()
    print("[SUCCESS] Inisialisasi Framework Berhasil!")
    print("-" * 70)
    print("Langkah Selanjutnya:")
    print("  1. Validasi build proyek:      .\\repo.bat build")
    print("  2. Buka Omniverse Editor:      .\\repo.bat launch")
    print("  3. Stream ke Web Dashboard:    .\\launch_web_view.bat")
    print("  4. Tambah level baru:          .\\add.bat level_02_detail")
    print("  5. Cek seluruh level:          .\\list_levels.bat")
    print("=" * 70)
    return 0


def cmd_add(args):
    """Scaffolds a new level file in levels/."""
    ext_name, ext_root, pkg_dir = resolve_extension_paths(args.extension)
    levels_dir = pkg_dir / "levels"

    if not levels_dir.is_dir():
        print(f"[ERROR] Direktori levels belum ada di '{ext_name}'. Jalankan .\\init_framework.bat {ext_name} terlebih dahulu.")
        sys.exit(1)

    raw_name = args.name.strip().lower()
    if not raw_name.startswith("level_"):
        raw_name = f"level_{raw_name}"

    clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", raw_name)
    file_name = f"{clean_id}.py"
    target_file = levels_dir / file_name

    if target_file.exists() and not args.force:
        print(f"[WARNING] File level '{file_name}' sudah ada di {target_file}!")
        print("Operasi dibatalkan untuk melindungi kode Anda. Gunakan --force jika ingin menimpa.")
        return 1

    class_name = to_pascal_case(clean_id) + "Handler"
    display_name = clean_id.replace("_", " ").title()

    template = read_template("level_template.py.txt")
    content = template.replace("{class_name}", class_name)
    content = content.replace("{level_id}", clean_id)
    content = content.replace("{display_name}", display_name)
    content = content.replace("{root_prim_path}", f"/World/{clean_id}")

    target_file.write_text(content, encoding="utf-8")

    (levels_dir / "__init__.py").touch(exist_ok=True)

    print("=" * 70)
    print(f"[SUCCESS] Berhasil membuat level baru di ekstensi '{ext_name}':")
    print(f"  - File:       {target_file}")
    print(f"  - Class:      {class_name}")
    print(f"  - Display:    {display_name}")
    print("=" * 70)
    print("Tips Penggunaan:")
    print(f"  - Buka {target_file} untuk menyesuaikan logic on_enter() dan on_exit()")
    print(f"  - Daftarkan navigasi: self.request_navigate('{clean_id}') dari level lain")
    print("=" * 70)
    return 0


def cmd_list(args):
    """Scans and displays all levels in the extension."""
    ext_name, ext_root, pkg_dir = resolve_extension_paths(args.extension)
    levels_dir = pkg_dir / "levels"

    print("=" * 75)
    print(f"  DAFTAR LEVEL AKTIF DI EKSTENSI: {ext_name}")
    print("=" * 75)

    if not levels_dir.is_dir():
        print(f"[INFO] Belum ada direktori levels/ di {ext_name}. Jalankan .\\init_framework.bat {ext_name} dahulu.")
        return 0

    level_files = sorted([f for f in levels_dir.glob("level_*.py") if f.is_file()])
    if not level_files:
        print(f"[INFO] Belum ada file level di folder levels/ ({ext_name}).")
        return 0

    print(f"{'No':<4} | {'Level ID':<22} | {'Class Name':<26} | {'Display Name'}")
    print("-" * 75)

    for idx, lfile in enumerate(level_files, start=1):
        content = lfile.read_text(encoding="utf-8")
        
        id_match = re.search(r'level_id\s*=\s*["\']([^"\']+)["\']', content)
        name_match = re.search(r'display_name\s*=\s*["\']([^"\']+)["\']', content)
        class_match = re.search(r'class\s+([a-zA-Z0-9_]+)\s*\(\s*BaseLevelHandler\s*\):', content)

        lvl_id = id_match.group(1) if id_match else lfile.stem
        display = name_match.group(1) if name_match else "-"
        cls_name = class_match.group(1) if class_match else "-"

        print(f"{idx:<4} | {lvl_id:<22} | {cls_name:<26} | {display}")

    print("=" * 75)
    print(f"Total: {len(level_files)} level terdaftar di '{ext_name}'.")
    return 0


def cmd_webview(args):
    """Generates or updates dedicated Web View Kit streaming app (cadit.web_view_only.kit)."""
    ext_name, ext_root, pkg_dir = resolve_extension_paths(args.extension)
    ws = get_workspace_root()
    print("=" * 70)
    print("  OMNIVERSE WEB VIEW STREAMING APP SCAFFOLDING")
    print("=" * 70)
    print(f"[WORKSPACE] Root: {ws}")
    print(f"[TARGET]    Ekstensi: '{ext_name}'")
    ensure_web_view_app(ws, ext_name, force=args.force)
    print("-" * 70)
    print("Selesai! Untuk menjalankan streaming:")
    print("  .\\launch_web_view.bat")
    print("=" * 70)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Omniverse Modular Extension Scaffolding Engine")
    subparsers = parser.add_subparsers(dest="command", help="Perintah yang tersedia")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Inisialisasi core architecture & helpers")
    init_parser.add_argument("extension", nargs="?", default=None, help="Nama ekstensi target (contoh: company.my_ext)")
    init_parser.add_argument("--force", action="store_true", help="Paksa tulis ulang meskipun sudah ada")

    # Command: add
    add_parser = subparsers.add_parser("add", help="Tambah level baru")
    add_parser.add_argument("name", help="Nama level (contoh: level_02_room atau room)")
    add_parser.add_argument("extension", nargs="?", default=None, help="Nama ekstensi target (opsional)")
    add_parser.add_argument("--force", action="store_true", help="Paksa timpa jika file sudah ada")

    # Command: list
    list_parser = subparsers.add_parser("list", help="Tampilkan daftar level yang terdaftar")
    list_parser.add_argument("extension", nargs="?", default=None, help="Nama ekstensi target (opsional)")

    # Command: webview
    webview_parser = subparsers.add_parser("webview", help="Buat/perbarui aplikasi streaming cadit.web_view_only.kit")
    webview_parser.add_argument("extension", nargs="?", default=None, help="Nama ekstensi target (opsional)")
    webview_parser.add_argument("--force", action="store_true", help="Paksa timpa file jika sudah ada")

    parsed = parser.parse_args()

    if parsed.command == "init":
        sys.exit(cmd_init(parsed))
    elif parsed.command == "add":
        sys.exit(cmd_add(parsed))
    elif parsed.command == "list":
        sys.exit(cmd_list(parsed))
    elif parsed.command == "webview":
        sys.exit(cmd_webview(parsed))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

