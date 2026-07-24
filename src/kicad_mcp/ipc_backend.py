"""Headless KiCad IPC backend (KiCad 11+ kicad-cli api-server + kicad-python)."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

logger = logging.getLogger("kicad-mcp.ipc")


class IpcHeadlessBackend:
    """Thread-safe wrapper around a headless kicad-cli api-server session."""

    def __init__(self, ipc_cli_path: str):
        self._ipc_cli_path = ipc_cli_path
        self._kicad: Any = None
        self._loaded_path: str | None = None
        self._lock = threading.Lock()

    @property
    def loaded_path(self) -> str | None:
        return self._loaded_path

    async def close(self) -> None:
        await asyncio.get_running_loop().run_in_executor(None, self._close_sync)

    def _close_sync(self) -> None:
        with self._lock:
            if self._kicad is not None:
                try:
                    self._kicad.close()
                except Exception as exc:
                    logger.warning("IPC session close: %s", exc)
                finally:
                    self._kicad = None
                    self._loaded_path = None

    async def send(self, method: str, params: dict | None = None) -> dict:
        return await asyncio.get_running_loop().run_in_executor(None, self._dispatch_sync, method, params or {})

    def _ensure_kicad(self, preload_path: str | None = None) -> dict | None:
        from kipy import KiCad

        target = preload_path or self._loaded_path
        if self._kicad is not None and preload_path and preload_path != self._loaded_path:
            try:
                self._kicad.close()
            except Exception:
                logger.exception("Failed to close KiCad IPC session")
            self._kicad = None
            self._loaded_path = None

        if self._kicad is None:
            kwargs: dict[str, Any] = {
                "headless": True,
                "kicad_cli_path": self._ipc_cli_path,
            }
            if target:
                kwargs["file_path"] = target
            self._kicad = KiCad(**kwargs)
            if not self._kicad.check_version():
                logger.warning("kicad-python version mismatch vs installed KiCad (continuing anyway)")
            if target:
                self._loaded_path = target
        elif target and not self._loaded_path:
            self._loaded_path = target
        return None

    def _board(self):
        if self._kicad is None:
            raise RuntimeError("IPC session not open")
        board = self._kicad.get_board()
        if board is None:
            raise RuntimeError("No PCB board open in headless session")
        return board

    def _layer_from_name(self, layer_name: str) -> int:
        from kipy.board_types import BoardLayer

        mapping = {
            "F.Cu": BoardLayer.BL_F_Cu,
            "B.Cu": BoardLayer.BL_B_Cu,
        }
        if layer_name in mapping:
            return mapping[layer_name]
        if hasattr(BoardLayer, layer_name):
            return getattr(BoardLayer, layer_name)
        raise ValueError(f"Unsupported layer for IPC backend: {layer_name}")

    def _dispatch_sync(self, method: str, params: dict) -> dict:
        handlers = {
            "ping": self._handle_ping,
            "status": self._handle_status,
            "pcb_load": self._handle_pcb_load,
            "pcb_info": self._handle_pcb_info,
            "pcb_list_components": self._handle_pcb_list_components,
            "pcb_list_nets": self._handle_pcb_list_nets,
            "pcb_list_tracks": self._handle_pcb_list_tracks,
            "pcb_get_component": self._handle_pcb_get_component,
            "pcb_place_component": self._handle_pcb_place_component,
            "pcb_add_track": self._handle_pcb_add_track,
            "pcb_add_via": self._handle_pcb_add_via,
            "pcb_save": self._handle_pcb_save,
            "pcb_set_board_outline": self._handle_pcb_set_board_outline,
            "pcb_drc": self._handle_pcb_drc,
            "pcb_export_step": self._handle_pcb_export_step,
        }
        handler = handlers.get(method)
        if handler is None:
            return {"success": False, "error": f"IPC method not implemented: {method}", "fallback": True}
        try:
            with self._lock:
                return handler(params)
        except ImportError as exc:
            return {
                "success": False,
                "error": f"kicad-python (kipy) not installed: {exc}. Run: uv sync --extra ipc",
                "fallback": True,
            }
        except Exception as exc:
            logger.exception("IPC %s failed", method)
            return {"success": False, "error": str(exc), "fallback": True}

    def _handle_ping(self, _params: dict) -> dict:
        self._ensure_kicad()
        self._kicad.ping()
        return {"success": True, "data": "pong"}

    def _handle_status(self, _params: dict) -> dict:
        self._ensure_kicad()
        version = self._kicad.get_version()
        return {
            "success": True,
            "data": {
                "ipc_headless": True,
                "kicad_version": version.full_version if version else "unknown",
                "board_loaded": self._loaded_path is not None,
                "board_file": self._loaded_path,
            },
        }

    def _handle_pcb_load(self, params: dict) -> dict:
        path = params.get("path", "")
        if not path:
            return {"success": False, "error": "path required"}
        self._ensure_kicad(path)
        return {"success": True, "data": {"path": path, "loaded": True, "backend": "ipc-headless"}}

    def _handle_pcb_info(self, _params: dict) -> dict:
        self._ensure_kicad()
        board = self._board()
        footprints = list(board.get_footprints())
        tracks = list(board.get_tracks())
        vias = list(board.get_vias())
        nets = list(board.get_nets())
        bbox = board.get_board_bounding_box()
        return {
            "success": True,
            "data": {
                "filename": self._loaded_path,
                "component_count": len(footprints),
                "net_count": len(nets),
                "track_count": len(tracks),
                "via_count": len(vias),
                "backend": "ipc-headless",
                "bounding_box_mm": {
                    "x": bbox.size.x / 1_000_000 if bbox else None,
                    "y": bbox.size.y / 1_000_000 if bbox else None,
                },
            },
        }

    def _handle_pcb_list_components(self, _params: dict) -> dict:
        from kipy.board_types import BoardLayer

        self._ensure_kicad()
        board = self._board()
        components = []
        for fp in board.get_footprints():
            ref = fp.reference_field.value if fp.reference_field else ""
            if not ref or ref.startswith("#"):
                continue
            lib_id = fp.definition.id if fp.definition and fp.definition.id else None
            components.append(
                {
                    "reference": ref,
                    "value": fp.value_field.value if fp.value_field else "",
                    "footprint": lib_id.name if lib_id else "",
                    "library": lib_id.library if lib_id else "",
                    "layer": "F.Cu" if fp.layer == BoardLayer.BL_F_Cu else "B.Cu",
                    "position_mm": {
                        "x": fp.position.x / 1_000_000,
                        "y": fp.position.y / 1_000_000,
                    },
                    "rotation_deg": fp.orientation.degrees if fp.orientation else 0,
                }
            )
        return {"success": True, "data": {"components": components, "count": len(components)}}

    def _handle_pcb_list_nets(self, _params: dict) -> dict:
        self._ensure_kicad()
        board = self._board()
        nets = []
        for net in board.get_nets():
            name = net.name or ""
            if not name or name == "":
                continue
            nets.append({"name": name, "code": getattr(net, "code", None)})
        return {"success": True, "data": {"nets": nets, "count": len(nets)}}

    def _handle_pcb_list_tracks(self, _params: dict) -> dict:
        self._ensure_kicad()
        board = self._board()
        tracks_out = []
        for track in board.get_tracks():
            tracks_out.append(
                {
                    "type": "TRACK",
                    "layer": str(track.layer),
                    "width_mm": track.width / 1_000_000,
                    "start_mm": {"x": track.start.x / 1_000_000, "y": track.start.y / 1_000_000},
                    "end_mm": {"x": track.end.x / 1_000_000, "y": track.end.y / 1_000_000},
                }
            )
        for via in board.get_vias():
            tracks_out.append(
                {
                    "type": "VIA",
                    "layer": "through",
                    "width_mm": via.diameter / 1_000_000 if via.diameter else None,
                    "start_mm": {"x": via.position.x / 1_000_000, "y": via.position.y / 1_000_000},
                    "end_mm": {"x": via.position.x / 1_000_000, "y": via.position.y / 1_000_000},
                    "diameter_mm": via.diameter / 1_000_000 if via.diameter else None,
                }
            )
        return {"success": True, "data": {"tracks": tracks_out, "count": len(tracks_out)}}

    def _handle_pcb_get_component(self, params: dict) -> dict:
        ref = params.get("reference", "")
        self._ensure_kicad()
        board = self._board()
        for fp in board.get_footprints():
            current = fp.reference_field.value if fp.reference_field else ""
            if current != ref:
                continue
            lib_id = fp.definition.id if fp.definition and fp.definition.id else None
            pads = []
            for pad in fp.definition.pads if fp.definition else []:
                pads.append(
                    {
                        "number": pad.number,
                        "net": pad.net.name if pad.net else "",
                    }
                )
            return {
                "success": True,
                "data": {
                    "reference": ref,
                    "value": fp.value_field.value if fp.value_field else "",
                    "footprint": lib_id.name if lib_id else "",
                    "library": lib_id.library if lib_id else "",
                    "position_mm": {"x": fp.position.x / 1_000_000, "y": fp.position.y / 1_000_000},
                    "rotation_deg": fp.orientation.degrees if fp.orientation else 0,
                    "pads": pads,
                },
            }
        return {"success": False, "error": f"Component '{ref}' not found"}

    def _handle_pcb_place_component(self, params: dict) -> dict:
        # Library footprint placement via IPC is still evolving on nightlies.
        return {
            "success": False,
            "error": (
                "pcb_place_component via IPC headless is not wired yet on this kicad-mcp build. "
                "Use KICAD_MCP_CRUD_BACKEND=tcp with kc_bridge.py, or track progress in docs/NIGHTLY_HEADLESS.md."
            ),
            "fallback": True,
        }

    def _handle_pcb_add_track(self, params: dict) -> dict:
        from kipy.board_types import Net, Track
        from kipy.geometry import Vector2
        from kipy.util import from_mm

        self._ensure_kicad()
        board = self._board()
        start = params.get("start_mm", {})
        end = params.get("end_mm", {})
        track = Track()
        track.start = Vector2.from_xy_mm(float(start.get("x", 0)), float(start.get("y", 0)))
        track.end = Vector2.from_xy_mm(float(end.get("x", 10)), float(end.get("y", 10)))
        track.width = from_mm(float(params.get("width_mm", 0.25)))
        track.layer = self._layer_from_name(params.get("layer", "F.Cu"))
        net_name = params.get("net_name", "")
        if net_name:
            track.net = Net(name=net_name)
        board.create_items(track)
        length_mm = track.length() / 1_000_000 if hasattr(track, "length") else None
        return {"success": True, "data": {"type": "TRACK", "length_mm": length_mm, "backend": "ipc-headless"}}

    def _handle_pcb_add_via(self, params: dict) -> dict:
        from kipy.board_types import Net, Via
        from kipy.geometry import Vector2
        from kipy.util import from_mm

        self._ensure_kicad()
        board = self._board()
        pos = params.get("position_mm", {})
        via = Via()
        via.position = Vector2.from_xy_mm(float(pos.get("x", 0)), float(pos.get("y", 0)))
        via.diameter = from_mm(float(params.get("diameter_mm", 0.6)))
        via.drill_diameter = from_mm(float(params.get("drill_mm", 0.3)))
        net_name = params.get("net_name", "")
        if net_name:
            via.net = Net(name=net_name)
        board.create_items(via)
        return {
            "success": True,
            "data": {
                "x_mm": float(pos.get("x", 0)),
                "y_mm": float(pos.get("y", 0)),
                "diameter_mm": float(params.get("diameter_mm", 0.6)),
                "backend": "ipc-headless",
            },
        }

    def _handle_pcb_save(self, params: dict) -> dict:
        self._ensure_kicad()
        board = self._board()
        path = params.get("path") or self._loaded_path
        if path:
            board.save_as(path, overwrite=True)
            self._loaded_path = path
        else:
            board.save()
        return {"success": True, "data": {"path": self._loaded_path, "backend": "ipc-headless"}}

    def _handle_pcb_set_board_outline(self, params: dict) -> dict:
        from kipy.board_types import BoardLayer, BoardPolygon
        from kipy.common_types import PolygonWithHoles
        from kipy.geometry import PolyLine, PolyLineNode
        from kipy.util import from_mm

        points = params.get("points", [])
        if len(points) < 3:
            return {"success": False, "error": "Need at least 3 points"}
        self._ensure_kicad()
        board = self._board()
        outline = PolyLine()
        for px, py in points:
            outline.append(PolyLineNode.from_xy(from_mm(float(px)), from_mm(float(py))))
        polygon = PolygonWithHoles()
        polygon.outline = outline
        shape = BoardPolygon()
        shape.layer = BoardLayer.BL_Edge_Cuts
        shape.polygons = [polygon]
        board.create_items(shape)
        return {"success": True, "data": {"vertices": len(points), "backend": "ipc-headless"}}

    def _handle_pcb_drc(self, _params: dict) -> dict:
        return {
            "success": False,
            "error": "DRC via IPC headless not used; call pcb_drc with stable kicad-cli instead",
            "fallback": True,
        }

    def _handle_pcb_export_step(self, _params: dict) -> dict:
        return {
            "success": False,
            "error": "STEP export via IPC not used; stable kicad-cli pcb export step is preferred",
            "fallback": True,
        }
