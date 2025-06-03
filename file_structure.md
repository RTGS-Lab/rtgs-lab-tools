rtgs-lab-tools/
├── pyproject.toml                         # Package configuration
├── README.md                              # Project documentation
├── .gitignore                             # Git ignore patterns
├── .env.template                          # Environment variables template
├── 
├── src/
│   └── rtgs_lab_tools/                    # Main package
│       ├── __init__.py                    # Package imports and version
│       │
│       ├── core/                          # Shared utilities
│       │   ├── __init__.py
│       │   ├── database.py                # Database connections
│       │   ├── config.py                  # Configuration management
│       │   ├── logging_utils.py           # Logging setup
│       │   └── exceptions.py              # Custom exceptions
│       │
│       ├── sensing_data/                  # GEMS database tools (migrate existing)
│       │   ├── __init__.py
│       │   ├── cli.py                     # CLI interface
│       │   └── extractor.py               # Core extraction logic
│       │
│       ├── gridded_data/                  # Climate/satellite data (new)
│       │   ├── __init__.py
│       │   ├── base_puller.py             # Base class for data sources
│       │   └── era5/                      # Start with ERA5 only
│       │       ├── __init__.py
│       │       ├── cli.py
│       │       └── puller.py
│       │
│       ├── visualization/                 # Data visualization (migrate existing)
│       │   ├── __init__.py
│       │   ├── cli.py
│       │   └── plotter.py
│       │
│       ├── device_management/             # Particle devices (migrate existing)
│       │   ├── __init__.py
│       │   ├── cli.py
│       │   ├── particle_api.py
│       │   └── configuration.py
│       │
│       └── mcp_server/                    # MCP integration
│           ├── __init__.py
│           ├── server.py                  # Main MCP server
│           └── tools.py                   # Tool definitions
│
├── tests/                                 # Basic test structure
│   ├── __init__.py
│   ├── test_core/
│   ├── test_sensing_data/
│   └── test_gridded_data/
│
└── examples/                              # Usage examples
    ├── basic_usage.py
    └── mcp_demo.py