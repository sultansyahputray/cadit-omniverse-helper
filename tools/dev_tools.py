# SPDX-FileCopyrightText: Copyright (c) 2026 CADIT. All rights reserved.
"""
Modular Project Template CLI & Scaffolding Engine.
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
    """Returns the workspace root directory (parent of tools/)."""
    return Path(__file__).resolve().parent.parent


def get_templates_dir() -> Path:
    """Returns the tools/templates directory."""
    return Path(__file__).resolve().parent / "templates"


def resolve_extension_paths(ext_name: str = None) -> tuple:
    """
    Resolves (ext_name, ext_root_dir, pkg_dir, pkg_name).
    Default target is cadit.modular_project.
    """
    ws = get_workspace_root()
    extensions_base = ws / "source" / "extensions"

    if not ext_name:
        ext_name = "cadit.modular_project"
        if not (extensions_base / ext_name).is_dir():
            # Scan source/extensions for available extensions
            candidates = [p.name for p in extensions_base.iterdir() if p.is_dir()]
            if candidates:
                ext_name = candidates[0]

    ext_root = extensions_base / ext_name
    if not ext_root.is_dir():
        print(f"[ERROR] Extension directory not found: {ext_root}")
        sys.exit(1)

    # Convert dot-separated ext name into directory path (e.g. cadit.modular_project -> cadit/modular_project)
    parts = ext_name.split(".")
    pkg_dir = ext_root.joinpath(*parts)

    # Fallback if package folder differs
    if not pkg_dir.is_dir():
        # Look for any folder with __init__.py inside ext_root
        for p in ext_root.rglob("__init__.py"):
            pkg_dir = p.parent
            break

    return ext_name, ext_root, pkg_dir


def to_pascal_case(snake_str: str) -> str:
    """Converts 'level_02_room' to 'Level02Room'."""
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


def cmd_init(args):
    """Initializes extension with Core, Four Helpers, and Starter Level 1."""
    ext_name, ext_root, pkg_dir = resolve_extension_paths(args.extension)
    manager_path = pkg_dir / "core" / "manager.py"

    print("=" * 70)
    print("  CADIT MODULAR PROJECT - FRAMEWORK INITIALIZATION")
    print("=" * 70)
    print(f"[CHECK] Memeriksa ekstensi target: '{ext_name}'")
    print(f"[PATH]  Package path: {pkg_dir}")

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
        print("  - Untuk memaksa reset total (HATI-HATI), gunakan: .\\init_framework.bat --force")
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

    # 9. Write core/base_level.py
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

    print()
    print("[SUCCESS] Inisialisasi Framework Berhasil!")
    print("-" * 70)
    print("Langkah Selanjutnya:")
    print("  1. Validasi build proyek:   .\\repo.bat build")
    print("  2. Jalankan aplikasi Kit:   .\\repo.bat launch")
    print("  3. Tambah level baru:       .\\add.bat level_02_detail")
    print("  4. Cek seluruh level:       .\\list_levels.bat")
    print("=" * 70)
    return 0


def cmd_add(args):
    """Scaffolds a new level file in levels/."""
    ext_name, ext_root, pkg_dir = resolve_extension_paths(args.extension)
    levels_dir = pkg_dir / "levels"

    if not levels_dir.is_dir():
        print(f"[ERROR] Direktori levels belum ada. Jalankan .\\init_framework.bat terlebih dahulu.")
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

    # Ensure levels/__init__.py exists
    (levels_dir / "__init__.py").touch(exist_ok=True)

    print("=" * 70)
    print(f"[SUCCESS] Berhasil membuat level baru: '{clean_id}'")
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
        print("[INFO] Belum ada direktori levels/. Jalankan .\\init_framework.bat dahulu.")
        return 0

    level_files = sorted([f for f in levels_dir.glob("level_*.py") if f.is_file()])
    if not level_files:
        print("[INFO] Belum ada file level di folder levels/.")
        return 0

    print(f"{'No':<4} | {'Level ID':<22} | {'Class Name':<26} | {'Display Name'}")
    print("-" * 75)

    for idx, lfile in enumerate(level_files, start=1):
        content = lfile.read_text(encoding="utf-8")
        
        # Regex extraction of metadata
        id_match = re.search(r'level_id\s*=\s*["\']([^"\']+)["\']', content)
        name_match = re.search(r'display_name\s*=\s*["\']([^"\']+)["\']', content)
        class_match = re.search(r'class\s+([a-zA-Z0-9_]+)\s*\(\s*BaseLevelHandler\s*\):', content)

        lvl_id = id_match.group(1) if id_match else lfile.stem
        display = name_match.group(1) if name_match else "-"
        cls_name = class_match.group(1) if class_match else "-"

        print(f"{idx:<4} | {lvl_id:<22} | {cls_name:<26} | {display}")

    print("=" * 75)
    print(f"Total: {len(level_files)} level terdaftar.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="CADIT Modular Project Scaffolding Engine")
    subparsers = parser.add_subparsers(dest="command", help="Perintah yang tersedia")

    # Command: init
    init_parser = subparsers.add_parser("init", help="Inisialisasi core architecture & helpers")
    init_parser.add_argument("extension", nargs="?", default="cadit.modular_project", help="Nama ekstensi target")
    init_parser.add_argument("--force", action="store_true", help="Paksa tulis ulang meskipun sudah ada")

    # Command: add
    add_parser = subparsers.add_parser("add", help="Tambah level baru")
    add_parser.add_argument("name", help="Nama level (contoh: level_02_room atau room)")
    add_parser.add_argument("extension", nargs="?", default="cadit.modular_project", help="Nama ekstensi target")
    add_parser.add_argument("--force", action="store_true", help="Paksa timpa jika file sudah ada")

    # Command: list
    list_parser = subparsers.add_parser("list", help="Tampilkan daftar level yang terdaftar")
    list_parser.add_argument("extension", nargs="?", default="cadit.modular_project", help="Nama ekstensi target")

    parsed = parser.parse_args()

    if parsed.command == "init":
        sys.exit(cmd_init(parsed))
    elif parsed.command == "add":
        sys.exit(cmd_add(parsed))
    elif parsed.command == "list":
        sys.exit(cmd_list(parsed))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
