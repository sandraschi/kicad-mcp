# kicad-mcp - MCP Server Capabilities

**Instructions for LLM:** This file must contain 3,000+ words describing the server's complete capabilities.
Include: all tools with parameters, all prompts, all resources, configuration options, environment variables,
data sources, and integration points. Every tool must have its purpose, parameters, and return format documented.

## Server Overview

[Write 2-3 paragraphs describing what this MCP server does, its domain, and key features.]

## Tools

- **fab_export**: Zip Gerber outputs for fabrication.
- **fab_order**: Create a fabrication order record.
- **fab_list_orders**: List fabrication order history.
- **fab_get_order**: fab_get_order
- **review_create**: review_create
- **review_list**: review_list
- **review_get**: review_get
- **review_annotate**: review_annotate
- **review_ai_audit**: review_ai_audit
- **kicad_status**: kicad_status
- **kicad_supported_commands**: kicad_supported_commands
- **api_status**: api_status
- **api_health**: api_health
- **api_diagnostics**: api_diagnostics
- **api_list_tools**: api_list_tools
- **api_list_skills**: api_list_skills
- **api_get_skill**: api_get_skill
- **api_llm_discover**: Probe Ollama and LM Studio, return detected providers + models.
- **api_llm_chat**: Proxy chat completion to local LLM (Ollama or OpenAI-compatible).
- **api_control_tool**: Dispatch REST calls to registered MCP tools by name.
- **api_upload**: Upload a KiCad project file (PCB, schematic, etc.).
- **api_list_files**: List files in uploads or outputs directory.
- **api_download**: Download a generated file from outputs or uploads.
- **api_boards_search**: Search GitHub for KiCad board projects.
- **api_component_detail**: Return mock component details for a part number or query.
- **api_board_preview**: api_board_preview
- **bom_generate**: bom_generate
- **lib_list_footprints**: lib_list_footprints
- **lib_list_symbols**: lib_list_symbols
- **lib_find_footprint**: lib_find_footprint
- **lib_find_symbol**: lib_find_symbol
- **fp_export_svg**: fp_export_svg
- **sym_export_svg**: sym_export_svg
- **marketplace_search**: marketplace_search
- **marketplace_categories**: marketplace_categories
- **marketplace_download**: marketplace_download
- **parts_search**: parts_search
- **parts_missing**: parts_missing
- **boards_search**: boards_search
- **boards_download**: boards_download
- **pcb_load**: pcb_load
- **pcb_info**: pcb_info
- **pcb_list_components**: pcb_list_components
- **pcb_list_nets**: pcb_list_nets
- **pcb_list_tracks**: pcb_list_tracks
- **pcb_get_component**: pcb_get_component
- **pcb_drc**: pcb_drc
- **pcb_export_step**: pcb_export_step
- **pcb_export_gerber**: pcb_export_gerber
- **pcb_export_pos**: pcb_export_pos
- **pcb_export_dxf**: pcb_export_dxf
- **pcb_export_svg**: pcb_export_svg
- **pcb_export_pdf**: pcb_export_pdf
- **pcb_export_vrml**: pcb_export_vrml
- **pcb_export_glb**: pcb_export_glb
- **pcb_export_ipc2581**: pcb_export_ipc2581
- **pcb_export_odbpp**: pcb_export_odbpp
- **pcb_place_component**: pcb_place_component
- **pcb_add_track**: pcb_add_track
- **pcb_add_via**: pcb_add_via
- **pcb_save**: pcb_save
- **pcb_set_board_outline**: pcb_set_board_outline
- **sch_load**: sch_load
- **sch_info**: sch_info
- **sch_erc**: sch_erc
- **sch_export_netlist**: sch_export_netlist
- **sch_export_python_bom**: sch_export_python_bom
- **sch_export_pdf**: sch_export_pdf
- **sch_export_svg**: sch_export_svg
- **sch_export_dxf**: sch_export_dxf

## Configuration

[Document all environment variables, their defaults, and purposes.]

## Data Sources

[Document any databases, APIs, or files the server reads.]
