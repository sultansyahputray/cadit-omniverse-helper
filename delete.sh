#!/usr/bin/env bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
if [ -z "$1" ]; then
    echo "[ERROR] Harap tentukan nama level yang ingin dihapus!"
    echo "Contoh penggunaan:"
    echo "  ./delete.sh level_02_room"
    echo "  ./delete.sh level_2_chiller [nama_ekstensi]"
    exit 1
fi
python "$SCRIPT_DIR/tools/dev_tools.py" delete "$@"
