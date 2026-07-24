"""Route PCB CRUD calls to IPC headless, TCP bridge, or none."""

from __future__ import annotations

from collections.abc import Awaitable, Callable


async def crud_send(
    state: dict,
    bridge_send: Callable[..., Awaitable[dict]],
    ipc_send: Callable[..., Awaitable[dict]] | None,
    method: str,
    params: dict | None = None,
) -> dict:
    """Dispatch a bridge-compatible JSON-RPC method to the active CRUD backend."""
    backend = state.get("crud_backend") or state.get("bridge_mode", "none")
    params = params or {}

    if backend == "ipc" and ipc_send is not None:
        return await ipc_send(method, params)

    if backend == "tcp":
        return await bridge_send(method, params)

    if backend == "ipc" and ipc_send is None:
        return {
            "success": False,
            "error": (
                "CRUD backend set to ipc but IPC session is unavailable. "
                "Install KiCad 11 nightly + uv sync --extra ipc. See docs/NIGHTLY_HEADLESS.md."
            ),
            "fallback": True,
        }

    return {
        "success": False,
        "error": (
            "No CRUD backend active. Install KiCad 11 nightly (IPC) or run kc_bridge.py in KiCad GUI (TCP). "
            "See docs/NIGHTLY_HEADLESS.md."
        ),
        "fallback": True,
    }
