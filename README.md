# CADIT Omniverse Helper

## Modular Multi-Level Architecture and Automation Toolkit for NVIDIA Omniverse Kit SDK

CADIT Omniverse Helper adalah kerangka kerja modular enterprise yang dirancang untuk standardisasi pengembangan aplikasi digital twin berbasis NVIDIA Omniverse Kit SDK. Toolkit ini menyediakan orkestrasi arsitektur multi-level, isolasi modifikasi layer USD non-destruktif, komputasi proyeksi koordinat 3D-ke-2D, serta jembatan komunikasi telemetri dua arah yang thread-safe dengan web dashboard eksternal.

---

## 1. Arsitektur Sistem dan Model Konkurensi

Toolkit ini membagi tanggung jawab arsitektural menjadi tiga layer utama:

```
+-----------------------------------------------------------------------------------+
|                           External Web Dashboard / IoT                            |
+-----------------------------------------------------------------------------------+
         | GET /api/telemetry (Status, Projections, Level Metrics)
         | POST /api/telemetry (Sensor Data, Alerts, External State)
         v POST /api/navigate, /api/camera, /api/select
+-----------------------------------------------------------------------------------+
|                        CADIT Omniverse Helper Core                                |
|                                                                                   |
|  [ TelemetryHelper Server ]                                                       |
|  - Embedded HTTP Server (Port 8089 dengan fallback 8088, 8090...)                 |
|  - Thread-Safe Command Queue (Mencegah thread collision pada USD Stage)           |
|  - State Caching per Level ID                                                     |
|                                                                                   |
|  [ LevelManager Orchestrator ]                                                    |
|  - Dynamic Auto-Discovery seluruh subclass BaseLevelHandler                       |
|  - Asynchronous USD Stage Switching (open_stage_async)                            |
|  - Context Tracking (History, Active Level, Previous Level)                       |
|  - Frame-Rate Dispatcher (60 FPS Update Loop)                                     |
+-----------------------------------------------------------------------------------+
|                           Level Handlers & Engines                                |
|                                                                                   |
|  BaseLevelHandler Subclasses:                                                     |
|  - level_01_default.py, level_02_room.py, level_03_rack.py, ...                   |
|                                                                                   |
|  Dedicated Helper Engines:                                                        |
|  - VisibilityHelper: Dynamic perspective cutaway & non-destructive hiding        |
|  - ProjectionHelper: Frustum projection 3D-ke-2D dengan dirty-check caching      |
|  - ColorHelper: Direct color injection pada USD SessionLayer                      |
|  - CameraHelper: Pivot-locked navigation & ViewCube presets                       |
|  - SelectionHelper: USD viewport selection synchronizer                           |
+-----------------------------------------------------------------------------------+
```

### Model Thread-Safety (USD Stage vs HTTP Worker Thread)
API OpenUSD (`pxr.Usd`) dan subsistem Omniverse Kit tidak dirancang untuk akses konkuren dari thread arbitrer. Request HTTP masuk melalui thread latar belakang (`threading.Thread`). `TelemetryHelper` memasukkan seluruh request mutasi ke dalam antrean aman (`queue.Queue`), yang kemudian diproses secara sinkron pada main thread Omniverse melalui `on_update(dt)` subscription stream Kit.

---

## 2. Spesifikasi Helper Engine

### 2.1 Telemetry and Web Bridge Helper (`TelemetryHelper`)
Menyediakan server REST API embedded yang menghubungkan status internal Omniverse dengan Web Dashboard (React, Vue, Three.js) dan sistem IoT eksternal.

#### Fitur Utama:
* **Auto-Port Binding:** Mencoba port 8089 secara default; jika port terpakai, otomatis mencoba port 8088, 8090, 8091, 8092, dan 8093.
* **CORS Support:** Header `Access-Control-Allow-Origin: *` aktif untuk seluruh request.
* **Namespaced Level Routing:** Routing data telemetri otomatis ke handler level yang dituju berdasarkan `level_id`.
* **State Caching:** Telemetri yang masuk untuk level yang sedang tidak aktif disimpan dalam memori dan otomatis dikirimkan saat level tersebut dibuka (`on_enter`).

#### Spesifikasi REST API Endpoints:

##### Endpoint: `GET /api/telemetry` atau `GET /api/status`
Mengambil status sistem, proyeksi koordinat 2D, dan telemetri level yang sedang aktif.

* **Query Parameters (Opsional):**
  * `aspect` (float): Rasio aspek viewport klien (contoh: `1.7777` untuk 16:9).
* **Format Response JSON:**
```json
{
  "status": "ok",
  "active_level": "level_02_room",
  "system": {
    "selected_prim": "/World/Room/Rack_01",
    "registered_levels": {
      "level_01_default": "Level 1 (Default Overview)",
      "level_02_room": "Room Overview"
    }
  },
  "projections": {
    "rack_01": {
      "x": 45.2,
      "y": 62.8,
      "visible": true
    },
    "chiller_01": {
      "x": 78.4,
      "y": 30.1,
      "visible": true
    }
  },
  "level_telemetry": {
    "level_id": "level_02_room",
    "data": {
      "ambient_temperature": 22.4,
      "chiller_power_kw": 45.0,
      "fire_alarm_active": false
    }
  }
}
```

##### Endpoint: `POST /api/telemetry`
Mengirimkan data telemetri atau alert eksternal ke dalam Omniverse.

* **Request Headers:**
  * `Content-Type: application/json`
  * `X-Level-Id: <level_id>` *(Opsional jika level_id dicantumkan pada body)*
* **Request Body JSON:**
```json
{
  "level_id": "level_02_room",
  "data": {
    "rack_01_status": "warning",
    "target_temperature": 20.5
  }
}
```
*Catatan:* Jika `level_id` tidak disertakan, data otomatis dialokasikan ke level yang sedang aktif saat ini.
* **Response JSON:**
```json
{
  "status": "ok",
  "level_id": "level_02_room",
  "cached": true
}
```

##### Endpoint: `POST /api/navigate`
Memicu transisi level dari remote dashboard.

* **Request Body JSON:**
```json
{
  "level": "level_02_room",
  "item_id": "rack_01"
}
```
* **Response JSON:**
```json
{
  "status": "ok",
  "target_level": "level_02_room"
}
```

##### Endpoint: `POST /api/camera`
Mengatur sudut pandang kamera atau level zoom viewport.

* **Request Body JSON (Pilihan Parameter):**
```json
{
  "view": "iso",
  "distance": 1200.0
}
```
Atau untuk framing objek:
```json
{
  "pivot_to": "/World/Room/Rack_01",
  "distance": 400.0
}
```
Atau untuk zoom bertahap:
```json
{
  "action": "zoom_in"
}
```

##### Endpoint: `POST /api/select`
Mengatur atau menghapus prim yang terseleksi di viewport.

* **Request Body JSON:**
```json
{
  "prim_path": "/World/Room/Rack_01"
}
```
Atau untuk menghapus seleksi:
```json
{
  "clear": true
}
```

---

### 2.2 Projection Helper Engine (`ProjectionHelper`)
Menghitung transformasi koordinat ruang 3D dunia ke ruang layar 2D (0.0% hingga 100.0% viewport) untuk disajikan sebagai overlay HTML/SVG/Canvas pada web dashboard.

#### Spesifikasi Teknis:
* **Frustum Math:** Menggunakan matriks `ViewProjection` kamera aktif di viewport.
* **Dirty-Check Caching:** Jika matriks posisi kamera dan rasio aspek tidak mengalami perubahan, helper menggunakan nilai cache tanpa kalkulasi ulang (0% pemakaian CPU frame).
* **Behind-Camera Clipping:** Objek yang berada di belakang bidang potong kamera (*near clipping plane*) secara otomatis ditandai dengan `"visible": false`.

#### Contoh Pemanggilan Python:
```python
# Registrasi objek yang ingin diproyeksikan pada level handler:
tracked_objects = {
    "rack_01": "/World/Room/Rack_01",
    "chiller_01": "/World/Room/Chiller_01"
}

# Mendapatkan posisi 2D:
positions = self.get_tracked_screen_positions(stage, client_aspect=1.777)
# Hasil:
# {
#     "rack_01": {"x": 52.3, "y": 44.1, "visible": True},
#     "chiller_01": {"x": 80.1, "y": 20.0, "visible": False}
# }
```

---

### 2.3 Direct Color, Emissive Glow, and Flow FX Engine (`ColorHelper`)
Mengubah material diffuse color, memancarkan efek pendaran cahaya (emissive glow), dan menghasilkan animasi pulsasi aliran (flow pulsing FX) pada prim secara dinamis tanpa mengubah file USD master di disk.

#### Spesifikasi Teknis:
* **SessionLayer Overrides:** Seluruh modifikasi warna dan material diaplikasikan pada `stage.GetSessionLayer()`. Asset master USD tetap bersih dari modifikasi runtime.
* **Format Warna Fleksibel:**
  * Hex String: `"#FF0000"`, `"#00E5FF"`, `"#888"`
  * Tuple RGB Float (0.0 - 1.0): `(1.0, 0.0, 0.0)`
  * Tuple RGB Int (0 - 255): `(255, 0, 0)`
* **Integrated Emissive Glow:**
  * Mendukung parameter `glow=True` dengan intensitas emisi kustom (`glow_intensity=3000.0` hingga `6000.0`).
  * Otomatis mengaktifkan post-processing RTX Bloom (`/rtx/post/bloom/enabled`) di Omniverse Kit tanpa konfigurasi render manual.
* **Sinusoidal Pulsing / Flow FX:**
  * Mendukung animasi denyut/aliran dinamis (`pulse=True`, `pulse_speed=1.5`) yang diperbarui secara otomatis pada loop frame. Cocok untuk visualisasi pipa MEP (listrik, pendingin) dan status darurat.
* **Recursive Submesh Traversal:** Otomatis menelusuri seluruh anak geometri (`UsdGeom.Mesh`, `UsdGeom.Subset`) di bawah root prim target.
* **State Restoration:** Menyimpan status material awal sebelum diubah, dan menyediakan method pemulihan total saat level ditinggalkan (`restore_all_colors`).

#### Contoh Pemanggilan Python:
```python
# 1. Memberikan warna standar (diffuse):
self.set_color(stage, "/World/Room/Rack_01", "#00FF88")

# 2. Memberikan efek pendaran cahaya (emissive glow) pada pipa:
self.set_glow(stage, "/World/Pipes/Cooling_Inlet", color="#00E5FF", intensity=5000.0)

# 3. Warna berpendar dengan denyut pulsasi (Flow FX atau status bahaya):
self.set_color(stage, "/World/Alarms/Beacon_01", "#FF2200", glow=True, pulse=True, pulse_speed=2.0)

# 4. Pemulihan ke kondisi awal:
self.restore_all_colors(stage)
```

---

### 2.4 Visibility Helper Engine (`VisibilityHelper`)
Mengatur visibilitas prim geometri secara dinamis dan non-destruktif.

#### Spesifikasi Teknis:
* **Static Hiding:** Menyembunyikan objek tertentu menggunakan API `UsdGeom.Imageable(prim).MakeInvisible()`.
* **Dynamic Perspective Cutaway:** Menghitung sudut dot product antara vektor normal bidang dinding dengan vektor pandang kamera secara real-time pada 60 FPS. Dinding yang menghalangi pandangan kamera otomatis menjadi transparan/hilang.
* **Non-Destructive Restoration:** Seluruh perubahan visibilitas dikembalikan ke status awal via `restore_all_visibility(stage)`.

#### Contoh Pemanggilan Python:
```python
# 1. Registrasi dinding untuk dynamic cutaway:
self.register_cutaway_walls({
    "north_wall": {"path": "/World/Room/Wall_North", "normal": (0, 1, 0)},
    "south_wall": {"path": "/World/Room/Wall_South", "normal": (0, -1, 0)},
    "east_wall":  {"path": "/World/Room/Wall_East",  "normal": (1, 0, 0)},
    "west_wall":  {"path": "/World/Room/Wall_West",  "normal": (-1, 0, 0)}
})

# 2. Update rutin pada loop frame (on_update):
def on_update(self, stage: Usd.Stage, dt: float) -> None:
    self.update_perspective_cutaway(stage, center=(0.0, 0.0, 0.0), dot_threshold=0.15)
```

---

### 2.5 Camera Navigation, ViewCube, and Smooth Glide Engine (`CameraHelper`)
Menyediakan kendali navigasi kamera viewport yang terukur, deterministik, dan dilengkapi transisi sinematik halus (*smooth glide interpolation*).

#### Spesifikasi Teknis:
* **Tumble Cursor Lockdown:** Mematikan opsi `tumbleAtCursor` Kit agar kamera tidak meloncat ke sembarang titik koordinat saat rotasi kursor dilakukan.
* **Industry-Standard ViewCube Presets:** Menyediakan sudut pandang ortogonal dan isometrik:
  * `"iso"`: Sudut isometrik standar CAD (azimuth 45°, elevasi 35.264°).
  * `"top"` / `"bottom"`: Pandangan atas dan bawah.
  * `"front"` / `"back"`: Pandangan depan dan belakang.
  * `"left"` / `"right"`: Pandangan samping kiri dan kanan.
* **Built-in Smooth Cinematic Glide (Interpolation):**
  * Setiap perubahan sudut pandang, framing objek, atau transisi level otomatis meluncur halus (*glide*) menggunakan kurva interpolasi *quintic smootherstep* (`6t^5 - 15t^4 + 10t^3`) yang menghilangkan sentakan percepatan dan perlambatan.
  * Parameter `smooth=True` (default) dan `duration=1.0` detik.
  * Dapat dinonaktifkan secara instan kapan saja menggunakan parameter `smooth=False` atau `duration=0.0`.
* **Object Pivot Focusing & Auto-Framing:** Memindahkan pusat orbit kamera tepat ke titik tengah (*centroid*) dari bounding box prim target (`set_camera_pivot_to_object`).
* **Stepped Zoom Controls:** Kendali zoom terukur melalui rasio perkalian (`camera_zoom_in`, `camera_zoom_out`).

#### Contoh Pemanggilan Python:
```python
# Berpindah ke sudut isometrik dengan glide sinematik selama 1.2 detik:
self.set_camera_view(stage, "iso", distance=1200.0, duration=1.2)

# Fokus ke objek tertentu dengan auto-framing dan transisi halus:
self.set_camera_pivot_to_object(stage, "/World/Room/Rack_01", distance=500.0)

# Pindah instan tanpa interpolasi (cut langsung):
self.set_camera_view(stage, "top", smooth=False)

# Zoom in bertahap:
self.camera_zoom_in(stage, factor=0.8)
```

---

### 2.6 Selection Helper Engine (`SelectionHelper`)
Mengatur sinkronisasi seleksi interaktif antara viewport Kit dengan level handler.

#### Spesifikasi Teknis:
* Terkoneksi langsung ke event stream seleksi `omni.usd.get_context().get_selection()`.
* Memicu pemanggilan callback `on_selection_changed(stage, prim_path)` pada level handler yang aktif saat pengguna mengklik objek di viewport.
* Mendukung seleksi dan pembatalan seleksi programmatik.

#### Contoh Pemanggilan Python:
```python
# Ambil prim yang sedang aktif diseleksi:
selected = self.get_selected_prim()

# Set seleksi secara kode:
self.set_selection("/World/Room/Chiller_01")

# Bersihkan seleksi:
self.clear_selection()
```

---

### 2.7 Metadata and Material Introspection Engine (`get_prim_metadata`)
Fasilitas ekstraksi metadata prim, bound material, bounding box dimensi, dan atribut custom USD ke dalam format serialisasi JSON murni.

#### Spesifikasi Teknis:
* **Recursive Material Search:** Jika prim induk tidak memiliki material langsung, mesin secara otomatis menelusuri *descendant prims* untuk menemukan `UsdShade.Material` yang terpasang pada submesh.
* **JSON-Safe Serializer:** Mengonversi tipe data OpenUSD internal (`GfVec3f`, `SdfPath`, `VtArray`, `TfToken`) menjadi tipe standar Python (`list`, `float`, `int`, `str`).

#### Contoh Pemanggilan Python:
```python
metadata = self.get_prim_metadata(stage, "/World/Room/Chiller_01")
# Output:
# {
#     "name": "Chiller_01",
#     "path": "/World/Room/Chiller_01",
#     "type": "Xform",
#     "material": {
#         "material_name": "M_ChillerSteel",
#         "material_path": "/World/Looks/M_ChillerSteel",
#         "binding_level": "direct (assigned to this prim)"
#     },
#     "bounds": {
#         "min": [-50.0, -25.0, 0.0],
#         "max": [50.0, 25.0, 120.0],
#         "dimensions": [100.0, 50.0, 120.0]
#     },
#     "attributes": { ... }
# }
```

---

## 3. Implementasi Level Handler (`BaseLevelHandler`)

Berikut adalah template implementasi production-ready untuk level ruangan (`level_02_room.py`):

```python
from typing import Dict, Any, Optional
from pxr import Usd, UsdGeom

from ..core.base_level import BaseLevelHandler
from ..core.context import NavigationContext


class Level02RoomHandler(BaseLevelHandler):
    level_id = "level_02_room"
    display_name = "Room Overview"
    root_prim_path = "/World/Room"

    # 1. Proyeksi koordinat 2D untuk Dashboard:
    tracked_objects = {
        "rack_01": "/World/Room/Rack_01",
        "chiller_01": "/World/Room/Chiller_01"
    }

    # 2. Konfigurasi Zoom saat klik objek:
    zoom_on_click = True
    click_zoom_distance = 600.0

    def __init__(self, manager):
        super().__init__(manager)
        self.room_temperature = 22.5
        self.hvac_status = "nominal"

    def on_enter(self, stage: Usd.Stage, context: NavigationContext) -> None:
        print(f"[{self.level_id}] Memasuki level dari: {context.previous_level}")

        # Atur kamera awal ke pandangan Isometrik:
        self.set_camera_view(stage, "iso", distance=1200.0)

        # Registrasi cutaway dinding ruangan:
        self.register_cutaway_walls({
            "wall_north": {"path": "/World/Room/Wall_North", "normal": (0, 1, 0)},
            "wall_south": {"path": "/World/Room/Wall_South", "normal": (0, -1, 0)}
        })

    def on_exit(self, stage: Usd.Stage, next_level_id: str) -> Dict[str, Any]:
        print(f"[{self.level_id}] Meninggalkan level menuju: {next_level_id}")

        # Wajib: Pulihkan seluruh status visual agar stage master tetap murni
        self.restore_all_visibility(stage)
        self.restore_all_colors(stage)
        self.reset_camera_pivot(stage)

        return {
            "last_temperature": self.room_temperature,
            "hvac_status": self.hvac_status
        }

    def on_update(self, stage: Usd.Stage, dt: float) -> None:
        # Update dynamic cutaway setiap frame:
        self.update_perspective_cutaway(stage, center=(0.0, 0.0, 0.0), dot_threshold=0.15)

    def on_selection_changed(self, stage: Usd.Stage, prim_path: Optional[str]) -> None:
        # Jalankan perilaku pivot dan auto-zoom bawaan:
        super().on_selection_changed(stage, prim_path)

        if prim_path:
            print(f"[{self.level_id}] Prim dipilih: {prim_path}")

    # --- Telemetry Integration Hooks ---
    def get_telemetry_payload(self) -> Dict[str, Any]:
        """Menyediakan data telemetri level ruangan ke Web Dashboard."""
        return {
            "room_temperature": self.room_temperature,
            "hvac_status": self.hvac_status,
            "active_alarms": 0
        }

    def on_telemetry_received(self, data: Dict[str, Any]) -> None:
        """Menangani data / instruksi yang dikirim oleh Web Dashboard."""
        print(f"[{self.level_id}] Menerima telemetri masuk:", data)

        # 1. Update nilai variabel lokal
        if "target_temperature" in data:
            self.room_temperature = float(data["target_temperature"])

        # 2. Respon visual di 3D berdasarkan alert
        rack_status = data.get("rack_01_status")
        stage = omni.usd.get_context().get_stage() if omni.usd.get_context() else None

        if stage and rack_status:
            if rack_status == "warning":
                self.set_color(stage, "/World/Room/Rack_01", "#FFB300")
            elif rack_status == "critical":
                self.set_color(stage, "/World/Room/Rack_01", "#FF2200")
            elif rack_status == "normal":
                self.color_helper.restore_color(stage, "/World/Room/Rack_01")
```

---

## 4. Panduan Integrasi Frontend Web (Client-Side)

Berikut adalah contoh hook integrasi React / TypeScript untuk berkomunikasi dengan Omniverse:

```typescript
import { useState, useEffect } from "react";

interface TelemetryResponse {
  active_level: string;
  system: {
    selected_prim: string | null;
    registered_levels: Record<string, string>;
  };
  projections: Record<string, { x: number; y: number; visible: boolean }>;
  level_telemetry: {
    level_id: string;
    data: Record<string, any>;
  };
}

export function useOmniverseBridge(baseUrl: string = "http://localhost:8089", intervalMs: number = 200) {
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [connected, setConnected] = useState<boolean>(false);

  useEffect(() => {
    const timer = setInterval(async () => {
      try {
        const aspect = window.innerWidth / window.innerHeight;
        const res = await fetch(`${baseUrl}/api/telemetry?aspect=${aspect.toFixed(3)}`);
        if (res.ok) {
          const json: TelemetryResponse = await res.json();
          setTelemetry(json);
          setConnected(true);
        }
      } catch (err) {
        setConnected(false);
      }
    }, intervalMs);

    return () => clearInterval(timer);
  }, [baseUrl, intervalMs]);

  // Fungsi pengiriman telemetri / alert ke Omniverse:
  const sendTelemetry = async (levelId: string, data: Record<string, any>) => {
    await fetch(`${baseUrl}/api/telemetry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level_id: levelId, data }),
    });
  };

  // Fungsi navigasi level:
  const navigateToLevel = async (levelId: string) => {
    await fetch(`${baseUrl}/api/navigate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: levelId }),
    });
  };

  return { telemetry, connected, sendTelemetry, navigateToLevel };
}
```

---

## 5. Alur Kerja CLI dan Otomasi Proyek

Helper dilengkapi dengan script CLI `dev_tools.py` yang dapat dijalankan secara instan melalui batch script di root proyek.

### Inisialisasi Proyek Baru
```bash
# Inisialisasi arsitektur core dan level default ke ekstensi target:
.\cadit-omniverse-helper\init_framework.bat company.my_extension
```

### Menambah Level Baru
```bash
# Menambah level baru secara mandiri:
.\add.bat level_02_room
.\add.bat level_03_chiller
```

### Memeriksa Daftar Level
```bash
# Menampilkan seluruh level yang terdaftar beserta nama kelasnya:
.\list_levels.bat
```

---

## 6. Lisensi dan Distribusi

Copyright (c) 2026 CADIT. All rights reserved.
Dokumen ini disusun sebagai panduan arsitektur teknis resmi untuk pengembangan sistem NVIDIA Omniverse Kit SDK berbasis multi-level modular framework.
