#!/usr/bin/env bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
if [ -z "$1" ]; then
    echo "[ERROR] Harap tentukan nama ekstensi target yang ingin diinisialisasi!"
    echo
    echo "Contoh penggunaan:"
    echo "  ./init_framework.sh company.my_extension"
    echo
fi
python "$SCRIPT_DIR/tools/dev_tools.py" init "$@"
