# Particle MCP Server

A Model Context Protocol server for the Particle IoT platform that enables AI assistants to manage Particle devices using natural language.

## Features

- Listing devices a part of your Particle organization

## Setup and Installation

create a .env file with the sctructure shown

```
# Particle API credentials
PARTICLE_ACCESS_TOKEN = your_api_token
```

to generate a particle api token, make sure the Particle CLI is installed and do this command:

```
particle token create
```

## Usage

Clone this repo

Open Claude Desktop

Navigate to Settings

Click Developer

Click Edit Config

Paste this in:
```
{
    "mcpServers": {
        "particle": {
            "command": "uv",
            "args": [
                "--directory",
                "DIRECT/PATH/TO/particle-mcp-server",
                "run",
                "particle.py"
            ]
        }
    }
}
```
## License

[Your chosen license]
