"""
KiCad TCP Bridge — runs inside KiCad's Python console for board manipulation.

This script is designed to be executed from within KiCad's Scripting Console
(Tools → Scripting Console) or passed as a startup script. It opens a TCP
socket and listens for JSON-RPC commands from the MCP server.

Supports both READ and WRITE operations on the BOARD object via pcbnew API.
Bridge-required operations (no kicad-cli equivalent):
    pcb_load, pcb_info, pcb_list_components, pcb_list_nets, pcb_list_tracks,
    pcb_get_component, pcb_place_component, pcb_add_track, pcb_add_via,
    pcb_save, pcb_set_board_outline, pcb_drc, pcb_export_step, ping, status

Environment:
    KC_BRIDGE_PORT — TCP port to listen on (default 11018)
"""

import json
import os
import socketserver
import sys
import traceback

PORT = int(os.environ.get("KC_BRIDGE_PORT", "11018"))

# ── KiCad imports (only available inside KiCad's Python) ─────────────────────
try:
    import pcbnew
except ImportError:
    pcbnew = None

_pcb: "pcbnew.BOARD | None" = None
_sch: object = None  # Schematic frame (only in GUI mode)


def _to_dict(obj):
    """Recursively convert KiCad objects to JSON-safe dicts."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(v) for v in obj]
    # pcbnew objects — extract attributes
    result = {}
    for attr in dir(obj):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(obj, attr)
            if callable(val):
                continue
            if isinstance(val, (str, int, float, bool, type(None))):
                result[attr] = val
            elif isinstance(val, (list, tuple)):
                result[attr] = str(val)
            else:
                result[attr] = str(val)
        except Exception:
            pass
    return result


def _load_board(path: str) -> dict:
    """Load a .kicad_pcb file into pcbnew."""
    global _pcb
    if pcbnew is None:
        return {"success": False, "error": "pcbnew not available"}
    try:
        _pcb = pcbnew.LoadBoard(path)
        return {"success": True, "data": {"path": path, "loaded": True}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_ping(_params):
    return {"data": "pong"}


def _handle_status(_params):
    return {
        "data": {
            "pcbnew_available": pcbnew is not None,
            "board_loaded": _pcb is not None,
            "board_file": _pcb.GetFileName() if _pcb else None,
        }
    }


def _handle_pcb_load(params):
    return _load_board(params["path"])


def _handle_pcb_info(_params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        design = _pcb.GetDesignSettings()
        components = list(_pcb.GetFootprints())
        nets = list(_pcb.GetNetInfo().NetsByName().values())
        bbox = _pcb.ComputeBoundingBox()
        return {
            "success": True,
            "data": {
                "filename": _pcb.GetFileName(),
                "layer_count": _pcb.GetCopperLayerCount(),
                "component_count": len(components),
                "net_count": len(nets) - 1,  # exclude unconnected
                "track_count": len(list(_pcb.GetTracks())),
                "via_count": len(list(filter(lambda t: t.Type() == pcbnew.PCB_VIA_T, _pcb.GetTracks()))),
                "bounding_box_mm": {
                    "x": pcbnew.ToMM(bbox.GetWidth()),
                    "y": pcbnew.ToMM(bbox.GetHeight()),
                    "origin_x": pcbnew.ToMM(bbox.GetOrigin().x),
                    "origin_y": pcbnew.ToMM(bbox.GetOrigin().y),
                },
                "design_rules": {
                    "min_track_width_mm": pcbnew.ToMM(design.GetMinTrackWidth()),
                    "min_via_diameter_mm": pcbnew.ToMM(design.GetMinViaDiameter()),
                    "min_clearance_mm": pcbnew.ToMM(design.GetSmallestClearanceValue()),
                },
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_list_components(_params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        components = []
        for fp in _pcb.GetFootprints():
            ref = fp.GetReference()
            if ref.startswith("#") or ref == "":
                continue
            components.append(
                {
                    "reference": ref,
                    "value": fp.GetValue(),
                    "footprint": str(fp.GetFPID().GetLibItemName()),
                    "library": str(fp.GetFPID().GetLibNickname()),
                    "layer": "F.Cu" if fp.GetLayer() == pcbnew.F_Cu else "B.Cu",
                    "position_mm": {
                        "x": pcbnew.ToMM(fp.GetPosition().x),
                        "y": pcbnew.ToMM(fp.GetPosition().y),
                    },
                    "rotation_deg": fp.GetOrientationDegrees(),
                }
            )
        return {"success": True, "data": {"components": components, "count": len(components)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_list_nets(_params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        net_info = _pcb.GetNetInfo()
        nets = []
        for name, net in net_info.NetsByName().items():
            pads = []
            for pad in net.Pads():
                pad_fp = pad.GetParent()
                if pad_fp:
                    pads.append(f"{pad_fp.GetReference()}-{pad.GetPadName()}")
            nets.append(
                {
                    "name": name,
                    "code": net.GetNetCode(),
                    "pad_count": len(pads),
                    "pads": pads,
                }
            )
        return {"success": True, "data": {"nets": nets, "count": len(nets)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_list_tracks(_params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        tracks = []
        for t in _pcb.GetTracks():
            ttype = "VIA" if t.Type() == pcbnew.PCB_VIA_T else "TRACK"
            info = {
                "type": ttype,
                "layer": str(t.GetLayerName()),
                "width_mm": pcbnew.ToMM(t.GetWidth()),
                "start_mm": {"x": pcbnew.ToMM(t.GetStart().x), "y": pcbnew.ToMM(t.GetStart().y)},
                "end_mm": {"x": pcbnew.ToMM(t.GetEnd().x), "y": pcbnew.ToMM(t.GetEnd().y)},
            }
            if ttype == "VIA":
                info["diameter_mm"] = pcbnew.ToMM(t.GetWidth())
            tracks.append(info)
        return {"success": True, "data": {"tracks": tracks, "count": len(tracks)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_get_component(params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    ref = params.get("reference", "")
    for fp in _pcb.GetFootprints():
        if fp.GetReference() == ref:
            pads = []
            for pad in fp.Pads():
                pads.append(
                    {
                        "number": pad.GetPadName(),
                        "net": pad.GetNet().GetNetname() if pad.GetNet() else "",
                        "position_mm": {"x": pcbnew.ToMM(pad.GetPosition().x), "y": pcbnew.ToMM(pad.GetPosition().y)},
                    }
                )
            return {
                "success": True,
                "data": {
                    "reference": ref,
                    "value": fp.GetValue(),
                    "footprint": str(fp.GetFPID().GetLibItemName()),
                    "library": str(fp.GetFPID().GetLibNickname()),
                    "layer": "F.Cu" if fp.GetLayer() == pcbnew.F_Cu else "B.Cu",
                    "position_mm": {"x": pcbnew.ToMM(fp.GetPosition().x), "y": pcbnew.ToMM(fp.GetPosition().y)},
                    "rotation_deg": fp.GetOrientationDegrees(),
                    "pads": pads,
                },
            }
    return {"success": False, "error": f"Component '{ref}' not found"}


def _handle_pcb_drc(params):
    """Run DRC and return violations."""
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        # KiCad 8+ DRC API
        drc_engine = pcbnew.DRC_ENGINE(_pcb, pcbnew.DRC_ENGINE.ALL_VIOLATIONS)
        drc_engine.InitEngine(pcbnew.ConvertStringToFilePos(_pcb.GetFileName()))
        drc_engine.RunTests(_pcb.GetFileName())
        violations = []
        for i in range(drc_engine.GetViolationCount()):
            v = drc_engine.GetViolation(i)
            violations.append(
                {
                    "id": i,
                    "type": str(v.GetViolationType()),
                    "message": v.GetViolationMessage(),
                    "severity": str(v.GetSeverity()),
                }
            )
        return {"success": True, "data": {"violations": violations, "count": len(violations)}}
    except AttributeError:
        pass  # Fall back to older API
    except Exception as e:
        return {"success": False, "error": str(e)}

    # Fallback: use kicad-cli for DRC
    return {"success": False, "error": "DRC via pcbnew API not available; use kicad-cli subprocess", "fallback": True}


def _handle_pcb_export_step(params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    path = params.get("path", "")
    if not path:
        return {"success": False, "error": "No output path specified"}
    try:
        _pcb.ExportSTEP(path)
        return {"success": True, "data": {"path": path}}
    except AttributeError:
        return {"success": False, "error": "STEP export via pcbnew API not available; use kicad-cli", "fallback": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_set_board_outline(params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    points = params.get("points", [])
    if len(points) < 3:
        return {"success": False, "error": "Need at least 3 points"}
    try:
        from pcbnew import PCB_SHAPE, SHAPE_T, Edge_Cuts, FromMM

        shape = PCB_SHAPE(_pcb, SHAPE_T.S_POLYGON)
        poly = shape.GetPolyShape()
        for px, py in points:
            poly.AddVertex(FromMM(px), FromMM(py))
        shape.SetLayer(Edge_Cuts)
        _pcb.Add(shape)
        pcbnew.Refresh()
        return {"success": True, "data": {"vertices": len(points)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_place_component(params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        lib_nick = params.get("library", "")
        fp_name = params.get("footprint", "")
        if not lib_nick or not fp_name:
            return {
                "success": False,
                "error": "library and footprint required (e.g. library='Resistor_SMD', footprint='R_US_0603')",
            }
        fp = pcbnew.FootprintLoad(lib_nick, fp_name)
        if fp is None:
            return {"success": False, "error": f"Footprint '{lib_nick}:{fp_name}' not found in libraries"}

        fp.SetReference(params.get("reference", "REF**"))
        fp.SetValue(params.get("value", "?"))
        pos = params.get("position_mm", {})
        fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pos.get("x", 0)), pcbnew.FromMM(pos.get("y", 0))))
        fp.SetOrientationDegrees(params.get("rotation_deg", 0.0))
        layer_name = params.get("layer", "F.Cu")
        fp.SetLayer(pcbnew.F_Cu if layer_name == "F.Cu" else pcbnew.B_Cu)
        _pcb.Add(fp)
        pcbnew.Refresh()
        return {"success": True, "data": {"reference": fp.GetReference(), "footprint": f"{lib_nick}:{fp_name}"}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_add_track(params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        track = pcbnew.PCB_TRACK(_pcb)
        start = params.get("start_mm", {})
        end = params.get("end_mm", {})
        track.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(start.get("x", 0)), pcbnew.FromMM(start.get("y", 0))))
        track.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(end.get("x", 0)), pcbnew.FromMM(end.get("y", 0))))
        track.SetWidth(pcbnew.FromMM(params.get("width_mm", 0.25)))
        layer_name = params.get("layer", "F.Cu")
        try:
            layer_id = (
                pcbnew.Layer.Layer_name_to_id(layer_name)
                if hasattr(pcbnew.Layer, "Layer_name_to_id")
                else {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}.get(layer_name, pcbnew.F_Cu)
            )
            track.SetLayer(layer_id)
        except Exception:
            track.SetLayer(pcbnew.F_Cu)
        net_name = params.get("net_name", "")
        if net_name:
            net = _pcb.GetNetInfo().GetNetItem(net_name)
            if net:
                track.SetNet(net.GetNetCode())
        _pcb.Add(track)
        pcbnew.Refresh()
        return {"success": True, "data": {"type": "track", "length_mm": _track_length_mm(track)}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _track_length_mm(track):
    dx = track.GetEnd().x - track.GetStart().x
    dy = track.GetEnd().y - track.GetStart().y
    return round(pcbnew.ToMM(int((dx**2 + dy**2) ** 0.5)), 4)


def _handle_pcb_add_via(params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    try:
        via = pcbnew.PCB_VIA(_pcb)
        pos = params.get("position_mm", {})
        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(pos.get("x", 0)), pcbnew.FromMM(pos.get("y", 0))))
        via.SetWidth(pcbnew.FromMM(params.get("diameter_mm", 0.6)))
        via.SetDrill(pcbnew.FromMM(params.get("drill_mm", 0.3)))
        via.SetViaType(pcbnew.VIA_THROUGH)
        net_name = params.get("net_name", "")
        if net_name:
            net = _pcb.GetNetInfo().GetNetItem(net_name)
            if net:
                via.SetNet(net.GetNetCode())
        _pcb.Add(via)
        pcbnew.Refresh()
        return {
            "success": True,
            "data": {"x_mm": pos.get("x"), "y_mm": pos.get("y"), "diameter_mm": params.get("diameter_mm", 0.6)},
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _handle_pcb_save(params):
    if _pcb is None:
        return {"success": False, "error": "No board loaded"}
    path = params.get("path", _pcb.GetFileName())
    if not path:
        return {"success": False, "error": "No path specified and board has no filename"}
    try:
        pcbnew.SaveBoard(path, _pcb)
        return {"success": True, "data": {"path": path, "saved": True}}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ── Request router ───────────────────────────────────────────────────────────

HANDLERS = {
    "ping": _handle_ping,
    "status": _handle_status,
    "pcb_load": _handle_pcb_load,
    "pcb_info": _handle_pcb_info,
    "pcb_list_components": _handle_pcb_list_components,
    "pcb_list_nets": _handle_pcb_list_nets,
    "pcb_list_tracks": _handle_pcb_list_tracks,
    "pcb_get_component": _handle_pcb_get_component,
    "pcb_drc": _handle_pcb_drc,
    "pcb_export_step": _handle_pcb_export_step,
    "pcb_set_board_outline": _handle_pcb_set_board_outline,
    "pcb_place_component": _handle_pcb_place_component,
    "pcb_add_track": _handle_pcb_add_track,
    "pcb_add_via": _handle_pcb_add_via,
    "pcb_save": _handle_pcb_save,
}


class BridgeHandler(socketserver.StreamRequestHandler):
    def handle(self):
        for line in self.rfile:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line.decode("utf-8"))
                method = req.get("method", "")
                params = req.get("params", {})
                rid = req.get("id", 0)

                handler = HANDLERS.get(method)
                if handler:
                    try:
                        result = handler(params)
                    except Exception as e:
                        result = {"success": False, "error": str(e), "traceback": traceback.format_exc()}
                else:
                    result = {"success": False, "error": f"Unknown method: {method}"}

                result["id"] = rid
                self.wfile.write((json.dumps(result, default=str) + "\n").encode("utf-8"))
                self.wfile.flush()
            except json.JSONDecodeError:
                pass
            except (BrokenPipeError, ConnectionResetError):
                break


def main():
    server = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), BridgeHandler)
    print(f"KiCad bridge listening on 127.0.0.1:{PORT}")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
