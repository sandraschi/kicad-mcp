# Board Marketplace — Downloading KiCad Projects

KiCad MCP can search GitHub for real PCB projects and download them into your workspace. This doc explains how it works, what you get, and how to use downloaded boards.

---

## What is the Board Marketplace?

A search engine over GitHub that finds KiCad PCB projects, filters out complex/industrial boards, and lets you download the source files with one click.

**What's searched:** GitHub repos with `topic:kicad` — thousands of open-source hardware projects.

**What's filtered out (you won't see these):**
- Motherboards, backplanes, server boards
- ATX, E-ATX, Mini-ITX form factors
- 8-layer / 10-layer / 12-layer / 16-layer boards
- FPGA dev boards, PCIe risers, GPU mining rigs
- High-end networking (switches, routers)

**What's prioritized (these score highest):**
- Raspberry Pi HATs and pHATs
- Arduino shields and breakouts
- STM32, ESP32, ESP8266 dev boards
- Sensor boards (temperature, IMU, environmental)
- Motor drivers, relay boards
- Audio DACs and amplifiers
- USB adapters and programmer boards
- Qwiic / Stemma / Grove breakouts
- Prototype and evaluation boards

Boards are scored **0–10** by hobbyist-friendliness. Higher score = simpler, better documented, more likely to be useful for your own projects.

---

## How to Use

### Via the Web Dashboard

1. Open `http://localhost:11017/boards`
2. Type a search like `raspberry pi hat` or `stm32 breakout` or `audio dac`
3. Browse results — each card shows:
   - Repo name, star count, description, topics
   - **Simplicity score** (green = great for hacking, amber = decent)
4. Click **Download KiCad Files** — the repo ZIP is fetched and `.kicad_pcb` / `.kicad_sch` files are extracted into the uploads directory

### Via Claude (MCP Tools)

```python
# Search
await boards_search(q="esp32 sensor")
await boards_search(q="motor driver", per_page=10)

# Download
await boards_download(repo="sandraschi/esp32-breakout")
```

### Via REST API

```powershell
curl http://127.0.0.1:11016/api/v1/boards?q=raspberry+pi+hat&per_page=20
```

---

## What You Get

When you download a board, you get:

| File type | Extension | What it is |
|-----------|-----------|------------|
| PCB layout | `.kicad_pcb` | The board itself — layers, tracks, components, vias |
| Schematic | `.kicad_sch` | The circuit diagram — symbols, nets, values |

Files are saved to `%TEMP%\kicad_mcp_work\uploads\` with a prefix like `owner_repo_filename.kicad_pcb` so downloads from different repos don't collide.

**What you DON'T get (usually):**
- The full repo with documentation, datasheets, 3D models, and firmware
- A ready-to-manufacture board (always run DRC before ordering)
- The design rationale — why they chose that capacitor value or that trace width

Downloaded boards are **starting points** — study them, learn from them, modify them.

---

## How Downloads Feed Into the Workflow

```
Download → uploads/ directory
              ↓
     Dashboard 3D viewer → pick board → see it in 3D
              ↓
     Claude can inspect it:
       pcb_info("board.kicad_pcb")  → component list
       pcb_drc("board.kicad_pcb")   → design rule check
       pcb_list_components(...)     → BOM preview
       sch_info("board.kicad_sch")  → schematic metadata
```

You can also use them as reference designs:
- "Find me USB-C power delivery boards like this one"
- "Download that STM32 dev board and place the same MCU on my design"
- "Show me how they routed the differential pair on this Raspberry Pi camera board"

---

## Limitations

**Not all KiCad repos are useful.** Many are:
- Unfinished or experimental (check the commit history)
- Missing schematic files (only `.kicad_pcb` with no `.kicad_sch`)
- Locked to specific KiCad versions (format may not open in yours)
- Dependencies on proprietary or hard-to-source parts

A score of **8+** usually means a well-documented, complete, working project.

**GitHub API rate limits** apply — 60 requests/hour without a token, 5000/hour with `GITHUB_TOKEN` set. Set one in your `.env` for regular use.

---

## Tips

| Goal | Search query | Why |
|------|-------------|-----|
| Learn USB-C design | `usb c breakout` | Simple, well-understood, many examples |
| Find an STM32 reference | `stm32 minimum` | Minimal system — learn what's essential |
| Build a sensor board | `temperature sensor breakout` | I2C/SPI breakouts are well-documented |
| Make a Raspberry Pi accessory | `raspberry pi hat` | Standard form factor, lots of community designs |
| Study power supply design | `buck converter` | Switch-mode supplies on 2-layer boards |
