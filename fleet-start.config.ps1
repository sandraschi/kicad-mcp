# Per-repo fleet start config for kicad-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'kicad-mcp'
    BackendPort  = 11016
    FrontendPort = 11017
    HealthPath   = '/api/v1/status'
    WebRoot      = 'D:\Dev\repos\kicad-mcp\webapp'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'kicad_mcp.server:app'
        SyncExtras    = @('dev')
        Env           = @{ WEB_PORT = '11016' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
