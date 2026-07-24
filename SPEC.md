# KiCad MCP — Product Specification

## Overview

Transform kicad-mcp from a tool-based automation server into a **full PCB design co-pilot** with an AI chat interface, real-time 3D visualization, and a complete fabrication-to-order pipeline.

---

## Feature 1: AI PCB Design Co-Pilot (Chat)

### Goal

A Chat page where the user describes board changes in natural language and the agent executes them via MCP tools. Powered by the local LLM (Ollama/LM Studio).

### Backend

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /api/v1/llm/discover` | GET | Probe Ollama :11434 and LM Studio :1234 for model lists |
| `POST /api/v1/llm/chat` | POST | Pass `{messages, system_prompt, model}` → stream response from Ollama |

**`POST /api/v1/llm/chat` request:**
```json
{
  "model": "llama3.2:latest",
  "system": "You are a PCB design assistant...",
  "messages": [{"role": "user", "content": "Place a 100nF cap near the IC"}],
  "stream": false
}
```

**Response:** `{"choices": [{"message": {"role": "assistant", "content": "..."}}]}`

### Frontend

**New pages:** `/chat`
**Components:** `ChatPage.tsx`, `ChatMessage.tsx`, `PersonalitySelect.tsx`, `ExamplePrompts.tsx`

| Component | Details |
|-----------|---------|
| Conversation memory | localStorage, 100-msg cap, ISO timestamps |
| Skill-first prompt | Fetch `GET /api/v1/skills` → load `kicad-mcp` skill as base preprompt |
| 4 personalities | PCB Designer (default), Component Specialist, DFM Reviewer, Custom |
| Example prompts | "Run DRC on my board", "Place a 0.1uF decoupling cap", "Export Gerbers for fabrication", "Add a via between F.Cu and B.Cu" |
| Export .txt | `kicad-mcp-chat-{timestamp}.txt` |
| Model selector | Editable text field, default from `/api/v1/llm/discover` |
| Provider status | Green/red indicator for Ollama/LM Studio |
| data-testid | `chat-page`, `chat-input`, `chat-send`, `personality-select`, `example-prompts` |

### Skill Preprompt

Create `src/kicad_mcp/skills/kicad-mcp/SKILL.md` with:
- Tool overview (PCB, Schematic, BOM, Library, Marketplace)
- Design workflow guidance
- Example sequences: "to place a component use pcb_place_component then pcb_add_track"
- Export pipeline guidance

**Expose via:** `GET /api/v1/skills` endpoint → reads SKILL.md from disk.

---

## Feature 2: 3D PCB Viewer (Dashboard)

### Goal

Render the current board as a 3D model on the Dashboard using Three.js. Show component placement, track routing, and board outline.

### Backend

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/board/view` | POST | Accept `{file_name}`, run `kicad-cli pcb export glb`, return URL to .glb file |
| `GET /api/v1/outputs/{file_name}` | GET | Serve generated files from OUTPUT_DIR |

### Frontend

Enhance `Dashboard.tsx` with a `PcbViewer3D.tsx` component:

| Capability | Detail |
|------------|--------|
| GLB/STEP loading | Three.js GLTFLoader for .glb, fallback to procedural board outline if no export |
| Orbit controls | Zoom, rotate, pan |
| Layer visibility | Toggle F.Cu, B.Cu, silkscreen, solder mask |
| Component highlighting | Click component → show metadata (reference, value, footprint) |
| Auto-refresh | Poll `/api/v1/tools` every 15s — if pcb_load called, re-fetch model |

**Three.js packages already in deps:** ✅ `three`, `@types/three`

---

## Feature 3: Fabrication Pipeline (Fab Page)

### Goal

One-click from KiCad project → Gerber + drill export → zip → order via fab house API. Track order history.

### Backend

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/fab/export` | POST | Run `pcb_export_gerber` + `pcb_export_pos` → zip all files |
| `POST /api/v1/fab/order` | POST | Submit to JLCPCB API (mock in v1) |
| `GET /api/v1/fab/orders` | GET | List order history from SQLite |
| `GET /api/v1/fab/export/{id}/download` | GET | Download the fabricaton zip |

**SQLite table:**
```sql
CREATE TABLE fab_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_name TEXT, created_at TEXT, status TEXT,
  gerber_zip_path TEXT, fab_house TEXT, order_ref TEXT
);
```

### Frontend

**New pages:** `/fab`

| Section | Detail |
|---------|--------|
| **Export card** | Select board file → "Generate Gerbers" button → shows export progress |
| **Order form** | Board dimensions, layer count, quantity, PCB color, fab house select |
| **Order history** | Table of past orders with status badges, download link |
| **Pricing estimate** | Auto-calculated based on board size/layers/quantity (JLCPCB pricing model) |

---

## Feature 4: Supercharged Component Browser (Library)

### Goal

Replace the flat Library page with a parametric search UI that combines local KiCad library search + GitHub marketplace + SnapEDA + parametric filters.

### Backend

Enhance existing `marketplace_search` + `lib_find_footprint` with:

| New tool | Purpose |
|----------|---------|
| `lib_component_details` | Fetch full metadata + datasheet URLs for a component |
| `marketplace_parametric_search` | Filter by package (SOT-23, QFP, BGA), pins, manufacturer |

### Frontend

Enhance `LibraryPage.tsx`:

| Section | Detail |
|---------|--------|
| **Parametric filter bar** | Package type dropdown, pin count range, manufacturer text input |
| **Search results grid** | Card per component: thumbnail, name, package, manufacturer, "Place on board" button |
| **Detail panel** | Right-side slide-out with full metadata, datasheet link, 3D model preview |

---

## Feature 5: Design Review Dashboard

### Goal

Upload a board, annotate it with comments/markers, share a link, run AI-driven design rule suggestions.

### Backend

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `POST /api/v1/review/create` | POST | Create review from board file |
| `POST /api/v1/review/{id}/annotation` | POST | Add annotation (x, y, layer, comment, severity) |
| `GET /api/v1/review/{id}` | GET | Get review with annotations |
| `POST /api/v1/review/{id}/ai-audit` | POST | Run AI DRC analysis on board |

### Frontend

**New pages:** `/review/{id}`, `/reviews`

- Board SVG/rendered preview with annotation overlay
- Annotation list with severity color coding (red/amber/green)
- AI audit button → streams DRC suggestions
- Share link copy button

---

## Feature 6: Live KiCad WebSocket Bridge

### Goal

Real-time two-way sync between KiCad GUI and the webapp over WebSocket.

### Backend

| Endpoint | Type | Purpose |
|----------|------|---------|
| `/ws/board` | WebSocket | Stream board state changes (component added, track moved, etc.) |
| `/ws/bridge` | WebSocket | Proxy to KiCad bridge TCP socket |

### Frontend

- Dashboard shows live "KiCad Connected" indicator
- Library updates when components added in KiCad
- 3D viewer auto-updates when board changes

---

## Implementation Order

| Phase | Features | Est. effort |
|-------|----------|-------------|
| **1 — Core co-pilot** | Chat page + LLM discover + skill preprompt | ~500 lines |
| **2 — Visual feedback** | 3D viewer on Dashboard + GLB export | ~400 lines |
| **3 — Fabrication** | Fab page + Gerber zip + order table | ~400 lines |
| **4 — Library v2** | Parametric search + detail panel | ~300 lines |
| **5 — Review** | Design review + AI audit | ~300 lines |
| **6 — Live bridge** | WebSocket + real-time sync | ~400 lines |
