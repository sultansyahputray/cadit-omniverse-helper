# CADIT Omniverse Helper

> **Modular Multi-Level Architecture & Automation Toolkit for NVIDIA Omniverse Kit SDK**

CADIT Omniverse Helper adalah toolkit enterprise yang dirancang untuk mengotomasi arsitektur multi-level, multi-developer, dan modular pada aplikasi NVIDIA Omniverse Kit SDK. Toolkit ini mencegah merge conflicts Git, menghilangkan monolithic bottleneck files, serta melengkapi level handler dengan empat mesin helper utama.

---

## 🌟 Fitur Utama & Empat Pilar Helper

### 1. 👁️ Visibility Helper Engine
* **Static Hiding:** Sembunyikan objek tertentu secara aman (`hide_objects(["/World/Roof"])`).
* **Dynamic Perspective Cutaway:** Dinding transparan dinamis mengikuti sudut kamera secara real-time (60 FPS) berbasis vektor *dot product*.
* **Non-Destructive Restoration:** Otomatis memulihkan seluruh visibilitas prim ke kondisi awal saat level di-exit tanpa mengubah file master USD.

### 2. 🎯 Projection Helper Engine (3D-to-2D Screen Coordinates)
* **Web Dashboard Bridge:** Menghitung koordinat layar 2D (`0%` hingga `100%` viewport X/Y) dari objek 3D untuk disajikan ke UI Web (React/Vue/Three.js overlay).
* **Dirty-Check Caching:** 0% beban CPU jika kamera diam.
* **Camera Clipping:** Otomatis men-set `"visible": false` jika objek berada di belakang kamera.

### 3. 🎨 Direct Color Injection Engine
* **Unopinionated & Fleksibel:** Mendukung format Hex (`"#00E5FF"`), tuple RGB Float `(0.0, 1.0, 0.0)`, maupun RGB Int `(0, 255, 0)`.
* **Submesh Recursive:** Otomatis mewarnai seluruh submesh dan subset geometri di bawah prim target.
* **SessionLayer Overrides:** Perubahan dilakukan di `SessionLayer`, aman untuk master stage, dan memiliki fitur `restore_all_colors()` saat berpindah level.

### 4. 🎥 Camera Navigation & ViewCube Engine
* **Pivot Terkunci di `(0, 0, 0)`:** Mematikan settingan kursor liar Kit (`tumbleAtCursor = False`) sehingga kamera berputar stabil pada pusat poros.
* **Fokus Poros ke Objek:** Memindahkan poros orbit ke titik tengah bounding box objek tertentu (`set_camera_pivot_to_object()`).
* **ViewCube Presets:** Pintasan sudut pandang standar industri: `"iso"`, `"top"`, `"front"`, `"back"`, `"left"`, `"right"`, `"bottom"`.
* **Zoom Controls:** Zoom bertahap (`camera_zoom_in`, `camera_zoom_out`), set distance, serta `zoom_to_fit_object()`.

---

## 🚀 Panduan Penggunaan di Proyek Omniverse Kit

### 1. Integrasi ke Proyek Kit SDK
Cukup letakkan folder `tools/` dan file batch shortcut (`init_framework.bat`, `add.bat`, `list_levels.bat`) di root folder proyek Omniverse Kit SDK Anda:

```text
my-omniverse-project/
├── init_framework.bat
├── add.bat
├── list_levels.bat
├── tools/
│   ├── dev_tools.py
│   └── templates/
└── source/
    └── extensions/
        └── my_company.my_extension/
```

### 2. Inisialisasi Arsitektur Core
Jalankan inisialisasi framework untuk ekstensi target Anda:

```bash
.\init_framework.bat my_company.my_extension
```

*Jika nama ekstensi tidak ditentukan, sistem otomatis mendeteksi ekstensi pertama di dalam `source/extensions`.*

> **🛡️ Proteksi Idempotensi (Anti-Overwrite):**
> Jika ekstensi sudah terinisialisasi sebelumnya, script akan menolak menimpa file Anda dan menjaga kode Anda tetap aman. Gunakan flag `--force` jika benar-benar ingin mereset total.

### 3. Menambah Level Baru
Setiap developer dapat membuat level baru secara instan dan mandiri tanpa konflik merge Git:

```bash
.\add.bat level_02_room
.\add.bat level_03_chiller
```

File baru akan otomatis terbuat di `source/extensions/<ext>/.../levels/level_*.py`.

### 4. Melihat Daftar Level Aktif
Inspeksi seluruh level yang terdaftar di dalam ekstensi:

```bash
.\list_levels.bat
```

---

## 📝 Contoh Implementasi Level Handler

```python
from typing import Dict, Any
from pxr import Usd, UsdGeom
from ..core.base_level import BaseLevelHandler
from ..core.context import NavigationContext


class Level02RoomHandler(BaseLevelHandler):
    level_id = "level_02_room"
    display_name = "Room Overview"
    root_prim_path = "/World/Room"

    # 1. Objek yang diproyeksikan koordinat layarnya untuk Web Dashboard:
    tracked_objects = {
        "rack_01": "/World/Room/Rack_01",
        "chiller_01": "/World/Room/Chiller_01"
    }

    # 2. Variabel warna level:
    highlight_color = "#00E5FF"

    def on_enter(self, stage: Usd.Stage, context: NavigationContext) -> None:
        print(f"[{self.level_id}] Entered from {context.previous_level}")

        # Atur kamera awal
        self.set_camera_pivot(stage, pivot_point=(0.0, 0.0, 0.0), distance=800.0)
        self.set_camera_view(stage, "iso")

        # Inject warna status
        self.set_color(stage, "/World/Room/Chiller_01", self.highlight_color)

    def on_exit(self, stage: Usd.Stage, next_level_id: str) -> Dict[str, Any]:
        # Pulihkan seluruh perubahan agar tidak merusak stage master
        self.restore_all_visibility(stage)
        self.restore_all_colors(stage)
        self.reset_camera_pivot(stage)

        return {"last_level": self.level_id}

    def on_update(self, stage: Usd.Stage, dt: float) -> None:
        # Loop update 60 FPS
        pass
```

---

## 📄 Lisensi

Copyright (c) 2026 CADIT. All rights reserved.
Didistribusikan untuk pengembangan aplikasi Omniverse Kit SDK berstandar modular.
