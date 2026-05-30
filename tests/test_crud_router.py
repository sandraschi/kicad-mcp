"""Tests for CRUD backend routing."""

from __future__ import annotations

import pytest

from kicad_mcp.crud_router import crud_send


@pytest.mark.asyncio
async def test_crud_send_none_backend():
    state = {"crud_backend": "none"}

    async def bridge(_method, _params):
        return {"success": True}

    result = await crud_send(state, bridge, None, "pcb_info", {})
    assert result["success"] is False
    assert "NIGHTLY_HEADLESS" in result["error"]


@pytest.mark.asyncio
async def test_crud_send_ipc_preferred():
    state = {"crud_backend": "ipc"}

    async def bridge(_method, _params):
        return {"success": True, "data": "tcp"}

    async def ipc(_method, _params):
        return {"success": True, "data": "ipc"}

    result = await crud_send(state, bridge, ipc, "pcb_info", {})
    assert result["data"] == "ipc"


@pytest.mark.asyncio
async def test_crud_send_tcp_when_ipc_unavailable():
    state = {"crud_backend": "tcp"}

    async def bridge(_method, _params):
        return {"success": True, "data": "tcp"}

    result = await crud_send(state, bridge, None, "pcb_info", {})
    assert result["data"] == "tcp"
