# CADIT Omniverse Helper

## Modular Multi-Level Architecture and Automation Toolkit for NVIDIA Omniverse Kit SDK

CADIT Omniverse Helper is an enterprise-grade modular framework designed to standardize and accelerate the development of digital twin applications on the NVIDIA Omniverse Kit SDK. The toolkit provides multi-level scene orchestration, non-destructive USD SessionLayer overrides, 3D-to-2D screen projection mathematics, and a thread-safe bidirectional telemetry bridge to external web dashboards and IoT platforms.

---

## 1. System Architecture and Concurrency Model

The toolkit organizes application responsibilities into three distinct architectural layers:

```
+-----------------------------------------------------------------------------------+
|                           External Web Dashboard / IoT                            |
+-----------------------------------------------------------------------------------+
         | GET /api/telemetry (System Status, 2D Projections, Level Metrics)
         | POST /api/telemetry (Sensor Data, Alarms, External State)
         v POST /api/navigate, /api/camera, /api/select
+-----------------------------------------------------------------------------------+
|                        CADIT Omniverse Helper Core                                |
|                                                                                   |
|  [ TelemetryHelper Server ]                                                       |
|  - Embedded HTTP Daemon (Port 8089 with auto-fallback to 8088, 8090, 8091...)      |
|  - Thread-Safe Command Queue (Guarantees USD Stage thread safety)                 |
|  - Per-Level Ingress State Caching                                                |
|                                                                                   |
|  [ LevelManager Orchestrator ]                                                    |
|  - Dynamic Auto-Discovery of BaseLevelHandler Subclasses                          |
|  - Asynchronous USD Stage Switching (open_stage_async)                            |
|  - Context and Transition Tracking (Active, Previous, Selection History)          |
|  - Frame-Rate Dispatcher (60 FPS Update Loop Subscription)                        |
+-----------------------------------------------------------------------------------+
|                           Level Handlers & Engines                                |
|                                                                                   |
|  BaseLevelHandler Subclasses:                                                     |
|  - level_01_default.py, level_02.py, level_03_detail.py, ...                      |
|                                                                                   |
|  Specialized Helper Engines:                                                      |
|  - VisibilityHelper: Dynamic perspective cutaway & non-destructive hiding        |
|  - ProjectionHelper: 3D-to-2D frustum projection with dirty-check caching         |
|  - ColorHelper: Direct color and emissive glow injection on USD SessionLayer      |
|  - CameraHelper: Pivot-locked navigation, ViewCube presets & smooth glide         |
|  - SelectionHelper: Viewport selection event stream synchronizer                  |
+-----------------------------------------------------------------------------------+
```

### Thread-Safety Model (USD Stage vs. HTTP Worker Thread)
OpenUSD (`pxr.Usd`) and Omniverse Kit core subsystems require mutations to execute on the application main thread. Incoming HTTP requests arrive on background worker threads (`threading.Thread`). `TelemetryHelper` places all stage mutation requests into a thread-safe queue (`queue.Queue`), which is drained and executed synchronously on the Kit main thread inside the extension `on_update(dt)` subscription stream.

---

## 2. Core Helper Engines Specification

### 2.1 Telemetry and Web Bridge Helper (`TelemetryHelper`)
An embedded HTTP daemon facilitating real-time telemetry streaming and command execution between Omniverse and external web applications (React, Next.js, Vue, Three.js).

#### Key Capabilities:
* **Automatic Port Fallback:** Binds to port `8089` by default. If the port is in use, it gracefully falls back through `8088`, `8090`, `8091`, `8092`, and `8093`.
* **CORS Support:** Sends `Access-Control-Allow-Origin: *` headers on all responses.
* **Namespaced Routing:** Routes incoming payloads to the designated level handler based on `level_id`.
* **State Caching:** Telemetry delivered for inactive levels is held in memory and dispatched immediately upon level activation (`on_enter`).

#### REST API Endpoints Specification:

##### Endpoint: `GET /api/telemetry` or `GET /api/status`
Retrieves system status, 2D screen coordinate projections, and active level telemetry.

* **Query Parameters (Optional):**
  * `aspect` (float): Client viewport aspect ratio (e.g., `1.777` for 16:9).
* **Response Payload (JSON):**
```json
{
  "status": "ok",
  "active_level": "level_01_default",
  "system": {
    "selected_prim": "/World/MainBuilding",
    "registered_levels": {
      "level_01_default": "Level 1 (Default Overview)",
      "level_02": "Level 2"
    }
  },
  "projections": {
    "root_overview": {
      "x": 50.0,
      "y": 42.5,
      "width": 12.4,
      "visible": true
    }
  },
  "level_telemetry": {
    "level_id": "level_01_default",
    "data": {
      "status": "online",
      "active_prim": "/World"
    }
  }
}
```

##### Endpoint: `POST /api/telemetry`
Transmits sensor data, alert states, or command payloads from the web dashboard into Omniverse.

* **Request Headers:**
  * `Content-Type: application/json`
  * `X-Level-Id: <level_id>` *(Optional if specified in JSON body)*
* **Request Payload (JSON):**
```json
{
  "level_id": "level_01_default",
  "data": {
    "command": "highlight_alert",
    "target_prim": "/World/Pump_01"
  }
}
```
* **Response Payload (JSON):**
```json
{
  "status": "ok",
  "level_id": "level_01_default",
  "cached": false
}
```

##### Endpoint: `POST /api/navigate`
Triggers an asynchronous level transition from the remote dashboard.

* **Request Payload (JSON):**
```json
{
  "level": "level_02",
  "item_id": "pump_01"
}
```
* **Response Payload (JSON):**
```json
{
  "status": "ok",
  "target_level": "level_02"
}
```

##### Endpoint: `POST /api/camera`
Controls viewport camera orientation, framing, and zoom factors.

* **Request Payload (JSON) Options:**
```json
{
  "view": "iso",
  "distance": 1200.0,
  "smooth": true,
  "duration": 1.0
}
```
To frame a specific object:
```json
{
  "pivot_to": "/World/Equipment/Chiller_01",
  "distance": 500.0
}
```
To perform incremental zoom:
```json
{
  "action": "zoom_in"
}
```

##### Endpoint: `POST /api/select`
Selects or deselects USD prims in the active viewport.

* **Request Payload (JSON):**
```json
{
  "prim_path": "/World/Equipment/Chiller_01"
}
```
Or to clear selection:
```json
{
  "clear": true
}
```

---

### 2.2 Projection Helper Engine (`ProjectionHelper`)
Transforms 3D USD world coordinates into normalized 2D viewport screen percentages (`0.0%` to `100.0%`), enabling HTML, SVG, and React UI overlays to align with 3D objects.

#### Technical Specifications:
* **Frustum Math:** Evaluates active viewport camera view-projection matrices.
* **Dirty-Check Caching:** If camera position, orientation, and client aspect ratio have not changed, cached coordinates are returned with zero frame-time overhead.
* **Near-Plane Clipping:** Objects located behind the camera near plane are flagged with `"visible": false`.
* **Projected Bounding Width:** Computes screen-space bounding percentage (`width`) to drive dynamic perspective zoom scaling on web tags.

#### Python Usage:
```python
# Static tracking defined in class body:
tracked_objects = {
    "main_unit": "/World/MainUnit"
}

# Dynamic tracking registered at runtime:
self.track_object("sensor_01", "/World/Sensors/Sensor_01", compute_bounds=True, anchor_point="top_center")

# Query screen coordinates:
positions = self.get_tracked_screen_positions(stage, client_aspect=1.777)
```

---

### 2.3 Color and Emissive Glow Engine (`ColorHelper`)
Applies diffuse colors, emissive glow materials, and pulsing status effects dynamically without modifying underlying USD files on disk.

#### Technical Specifications:
* **SessionLayer Overrides:** All edits are applied to `stage.GetSessionLayer()`. Master USD stage assets remain untouched.
* **Supported Color Formats:**
  * Hex strings: `"#00FFCC"`, `"#FF0000"`, `"#888"`
  * RGB float tuples `(0.0, 1.0, 0.5)`
  * RGB integer tuples `(0, 255, 128)`
* **Integrated Emissive Glow:** Enables RTX Bloom post-processing automatically (`/rtx/post/bloom/enabled`) and injects emissive shaders.
* **Sinusoidal Flow & Pulsing FX:** Provides dynamic breathing glow animations (`pulse=True`, `pulse_speed=1.5`) evaluated on the frame loop for alarms and fluid flows.
* **Recursive Submesh Traversal:** Automatically binds overrides across child `UsdGeom.Mesh` and `UsdGeom.Subset` instances.
* **Complete State Restoration:** Tracks pre-modification states and restores original materials upon exit (`restore_all_colors`).

#### Python Usage:
```python
# 1. Apply solid diffuse color:
self.set_color(stage, "/World/Equipment/Pump", "#00FF88")

# 2. Apply emissive glow:
self.set_glow(stage, "/World/Pipes/Cooling", color="#00E5FF", intensity=3500.0)

# 3. Apply pulsing alarm effect:
self.set_glow(stage, "/World/Alarms/Beacon", color="#FF2200", intensity=5000.0, pulse=True, pulse_speed=2.0)

# 4. Batch color multiple objects:
self.set_colors(stage, {
    "/World/Unit_A": "#00FF00",
    "/World/Unit_B": "#FFB300"
})

# 5. Restore original colors:
self.restore_all_colors(stage)
```

---

### 2.4 Visibility Helper Engine (`VisibilityHelper`)
Provides non-destructive visibility toggling and automated perspective cutaways.

#### Technical Specifications:
* **Non-Destructive Hiding:** Uses `UsdGeom.Imageable(prim).MakeInvisible()` tracked on the session layer.
* **Dynamic Perspective Cutaway:** Computes the dot product between wall surface normals and camera view vectors in real time (60 FPS). Walls obstructing the line of sight are hidden automatically.
* **Complete Restoration:** Resets all modified visibilities upon level transition via `restore_all_visibility(stage)`.

#### Python Usage:
```python
# 1. Register cutaway walls:
self.register_cutaway_walls({
    "wall_north": {"path": "/World/Room/Wall_North", "normal": (0, 1, 0)},
    "wall_south": {"path": "/World/Room/Wall_South", "normal": (0, -1, 0)},
    "wall_east":  {"path": "/World/Room/Wall_East",  "normal": (1, 0, 0)},
    "wall_west":  {"path": "/World/Room/Wall_West",  "normal": (-1, 0, 0)}
})

# 2. Update cutaway orientation in frame update loop:
def on_update(self, stage: Usd.Stage, dt: float) -> None:
    self.update_perspective_cutaway(stage, center=(0.0, 0.0, 0.0), dot_threshold=0.15)

# 3. Explicit hide and show:
self.hide_objects(stage, ["/World/Roof", "/World/Ceiling"])
self.show_objects(stage, ["/World/InternalMachinery"])
```

---

### 2.5 Camera Navigation and Smooth Glide Engine (`CameraHelper`)
Provides deterministic viewport camera positioning with quintic smootherstep interpolation.

#### Technical Specifications:
* **Tumble Cursor Lockdown:** Disables `tumbleAtCursor` in Omniverse preferences to prevent unexpected camera jumps during viewport navigation.
* **Standard ViewCube Presets:**
  * `"iso"`: CAD standard isometric perspective (azimuth 45°, elevation 35.264°).
  * `"top"`, `"bottom"`, `"front"`, `"back"`, `"left"`, `"right"`.
* **Cinematic Smooth Glide:** Transitions between poses using quintic smootherstep interpolation (`6t^5 - 15t^4 + 10t^3`), eliminating velocity jolts.
* **Centroid Auto-Framing:** Moves orbit pivots to the exact bounding-box centroid of any target prim (`set_camera_pivot_to_object`).
* **Stepped Zoom:** Proportional scaling factors (`camera_zoom_in`, `camera_zoom_out`).

#### Python Usage:
```python
# Glide smoothly to isometric angle over 1.2 seconds:
self.set_camera_view(stage, "iso", distance=1200.0, duration=1.2)

# Focus camera pivot to object:
self.set_camera_pivot_to_object(stage, "/World/Equipment/Rack_01", distance=500.0)

# Instant cut (no interpolation):
self.set_camera_view(stage, "top", smooth=False)

# Stepped zoom:
self.camera_zoom_in(stage, factor=0.8)
```

---

### 2.6 Selection Helper Engine (`SelectionHelper`)
Maintains synchronization between Omniverse viewport interactions and application code.

#### Technical Specifications:
* Subscribes to the USD selection event stream (`omni.usd.get_context().get_selection()`).
* Invokes `on_selection_changed(stage, prim_path)` on the active level handler whenever an object is clicked.
* Supports programmatic selection and deselection.

#### Python Usage:
```python
# Query active selection:
selected_prim = self.get_selected_prim()

# Set selection programmatically:
self.set_selection("/World/Equipment/Rack_01")

# Deselect:
self.clear_selection()
```

---

### 2.7 Metadata and Material Introspection Engine (`get_prim_metadata`)
Extracts prim metadata, bound materials, bounding dimensions, and custom attributes into standard Python dictionaries and serialized JSON.

#### Python Usage:
```python
metadata = self.get_prim_metadata(stage, "/World/Equipment/Pump")
# Output:
# {
#     "name": "Pump",
#     "path": "/World/Equipment/Pump",
#     "type": "Xform",
#     "material": {
#         "material_name": "M_MetalSteel",
#         "material_path": "/World/Looks/M_MetalSteel",
#         "binding_level": "direct (assigned to this prim)"
#     },
#     "bounds": {
#         "min": [-25.0, -25.0, 0.0],
#         "max": [25.0, 25.0, 60.0],
#         "dimensions": [50.0, 50.0, 60.0]
#     }
# }
```

---

## 3. Bundled Example Maps (`example_map`)

The repository includes a ready-to-use map directory at `cadit-omniverse-helper/example_map/` to facilitate immediate testing of multi-level transitions:

* `main_map.usd`: Primary overview scene utilized by Level 1 (`level_01_default`).
* `level_02_map.usd`: Detailed asset scene utilized by Level 2 (`level_02`).

When `LevelManager` initiates a transition (`navigate_to("level_02")`), it resolves relative map paths automatically, compares the current stage URL against the target, and asynchronously opens the new USD stage without requiring hardcoded absolute paths.

---

## 4. Production Level Handler Implementation (`BaseLevelHandler`)

Below is the clean production implementation pattern used by both `level_01_default.py` and `level_02.py`:

```python
from typing import Dict, Any, Optional
from pxr import Usd, UsdGeom

from ..core.base_level import BaseLevelHandler
from ..core.context import NavigationContext


class Level01DefaultHandler(BaseLevelHandler):
    level_id = "level_01_default"
    display_name = "Level 1 (Default Overview)"

    # USD Stage Map URL (relative to project root or absolute file path):
    map_url = "cadit-omniverse-helper/example_map/main_map.usd"
    root_prim_path = "/World"

    # 2D Screen Projection Tracking for Web Dashboard:
    tracked_objects = {
        "root_overview": "/World"
    }

    # Click-to-Zoom Configuration:
    zoom_on_click = True
    click_zoom_distance = None

    def __init__(self, manager):
        super().__init__(manager)
        self.selected_item = None

    def on_enter(self, stage: Usd.Stage, context: NavigationContext) -> None:
        print(f"[{self.level_id}] Activated. Map: {self.map_url}")

        # Set initial camera view to isometric:
        self.set_camera_view(stage, "iso", distance=1000.0, smooth=True)

        # Show built-in in-viewport level switcher overlay:
        self.show_level_navigator()

    def on_exit(self, stage: Usd.Stage, next_level_id: str) -> Dict[str, Any]:
        print(f"[{self.level_id}] Exiting to {next_level_id}")

        # Restore modified states:
        self.restore_all_visibility(stage)
        self.restore_all_colors(stage)
        self.reset_camera_pivot(stage)

        return {
            "from_level": self.level_id,
            "last_selection": self.selected_item
        }

    def on_update(self, stage: Usd.Stage, dt: float) -> None:
        pass

    def on_selection_changed(self, stage: Usd.Stage, prim_path: Optional[str]) -> None:
        self.selected_item = prim_path
        super().on_selection_changed(stage, prim_path)

    def get_telemetry_payload(self) -> Dict[str, Any]:
        return {
            "status": "online",
            "active_prim": self.selected_item or self.root_prim_path
        }

    def on_telemetry_received(self, data: Dict[str, Any]) -> None:
        print(f"[{self.level_id}] Telemetry received:", data)
```

---

## 5. Web Frontend Integration Guide

A React / TypeScript hook implementation connecting to the `TelemetryHelper` daemon:

```typescript
import { useState, useEffect } from "react";

interface TelemetryResponse {
  active_level: string;
  system: {
    selected_prim: string | null;
    registered_levels: Record<string, string>;
  };
  projections: Record<string, { x: number; y: number; width?: number; visible: boolean }>;
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

  const sendTelemetry = async (levelId: string, data: Record<string, any>) => {
    await fetch(`${baseUrl}/api/telemetry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level_id: levelId, data }),
    });
  };

  const navigateTo = async (levelId: string) => {
    await fetch(`${baseUrl}/api/navigate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level: levelId }),
    });
  };

  return { telemetry, connected, sendTelemetry, navigateTo };
}
```

---

## 6. Developer CLI Automation Workflow

The toolkit includes the `dev_tools.py` automation suite, accessible through root batch scripts:

### Initializing the Framework
Scaffolds core engines, helpers, and automatically generates two starter levels (`level_01_default.py` and `level_02.py`):
```bash
.\cadit-omniverse-helper\init_framework.bat company.my_extension
```

### Adding a New Level
Generates a new level handler pre-populated with clean helper examples:
```bash
.\add.bat level_03_chiller
```

### Listing Registered Levels
Scans the extension and displays all registered handlers:
```bash
.\list_levels.bat
```

### Launching Dedicated WebRTC Streaming App
Launches Omniverse Kit using the dedicated Web View streaming profile (`cadit.web_view_only.kit`):
```bash
.\launch_web_view.bat
```

---

## 7. License and Copyright

Copyright (c) 2026 CADIT. All rights reserved.
Developed for enterprise digital twin applications powered by the NVIDIA Omniverse Kit SDK.
