"""MCP server for RTGS Lab Tools."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

from ..core import Config, DatabaseManager, setup_logging
from ..core.exceptions import RTGSLabToolsError, DatabaseError, ConfigError
from ..sensing_data import get_raw_data, list_projects, get_nodes_for_project

logger = logging.getLogger(__name__)


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("rtgs-lab-tools")
    
    # Initialize global database manager
    db_manager = None
    
    def get_db_manager() -> DatabaseManager:
        """Get or create database manager instance."""
        nonlocal db_manager
        if db_manager is None:
            try:
                config = Config()
                db_manager = DatabaseManager(config)
                if not db_manager.test_connection():
                    raise DatabaseError("Failed to connect to database")
            except Exception as e:
                raise DatabaseError(f"Database initialization failed: {e}")
        return db_manager
    
    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """List available resources."""
        return [
            Resource(
                uri="rtgs://projects",
                name="Available Projects",
                description="List of all available sensing projects",
                mimeType="application/json"
            ),
            Resource(
                uri="rtgs://database-info",
                name="Database Information", 
                description="Information about the GEMS database connection",
                mimeType="text/plain"
            )
        ]
    
    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a specific resource."""
        if uri == "rtgs://projects":
            try:
                db = get_db_manager()
                projects = list_projects(db)
                return str(projects)
            except Exception as e:
                return f"Error fetching projects: {e}"
        
        elif uri == "rtgs://database-info":
            try:
                config = Config()
                return f"""GEMS Database Information
Host: {config.db_host}
Port: {config.db_port}
Database: {config.db_name}
Status: Connected
"""
            except Exception as e:
                return f"Database connection error: {e}"
        
        return f"Unknown resource: {uri}"
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools."""
        return [
            Tool(
                name="get_sensing_data",
                description="Extract raw sensor data from GEMS database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "Project name to query"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                            "default": "2018-01-01"
                        },
                        "end_date": {
                            "type": "string", 
                            "description": "End date in YYYY-MM-DD format (defaults to today)"
                        },
                        "node_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of specific node IDs"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of records to return",
                            "default": 1000
                        }
                    },
                    "required": ["project"]
                }
            ),
            Tool(
                name="list_projects",
                description="List all available sensing projects with node counts",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="get_project_nodes",
                description="Get nodes for a specific project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "Project name"
                        }
                    },
                    "required": ["project"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle tool calls."""
        try:
            db = get_db_manager()
            
            if name == "get_sensing_data":
                project = arguments["project"]
                start_date = arguments.get("start_date", "2018-01-01")
                end_date = arguments.get("end_date")
                node_ids = arguments.get("node_ids")
                limit = arguments.get("limit", 1000)
                
                if not end_date:
                    end_date = datetime.now().strftime("%Y-%m-%d")
                
                df = get_raw_data(
                    database_manager=db,
                    project=project,
                    start_date=start_date,
                    end_date=end_date,
                    node_ids=node_ids
                )
                
                if df.empty:
                    return [TextContent(
                        type="text",
                        text=f"No data found for project '{project}' between {start_date} and {end_date}"
                    )]
                
                # Apply limit
                if len(df) > limit:
                    df = df.head(limit)
                    truncated_msg = f" (showing first {limit} of {len(df)} records)"
                else:
                    truncated_msg = ""
                
                # Format response
                summary = f"Retrieved {len(df)} records{truncated_msg} from project '{project}'"
                
                if len(df) <= 10:
                    # Show full data for small datasets
                    data_preview = df.to_string(index=False)
                else:
                    # Show summary statistics for large datasets
                    data_preview = f"""
Data Summary:
- Records: {len(df)}
- Date range: {df['publish_time'].min()} to {df['publish_time'].max()}
- Nodes: {df['node_id'].nunique()} unique nodes
- Node IDs: {', '.join(df['node_id'].unique()[:10])}{'...' if df['node_id'].nunique() > 10 else ''}

First 5 records:
{df.head().to_string(index=False)}
"""
                
                return [TextContent(
                    type="text",
                    text=f"{summary}\n\n{data_preview}"
                )]
            
            elif name == "list_projects":
                projects = list_projects(db)
                if not projects:
                    return [TextContent(
                        type="text",
                        text="No projects found in the database"
                    )]
                
                project_list = "\n".join([f"  {name} ({count} nodes)" for name, count in projects])
                return [TextContent(
                    type="text",
                    text=f"Available projects ({len(projects)} total):\n{project_list}"
                )]
            
            elif name == "get_project_nodes":
                project = arguments["project"]
                nodes_df = get_nodes_for_project(db, project)
                
                if nodes_df.empty:
                    return [TextContent(
                        type="text",
                        text=f"No nodes found for project '{project}'"
                    )]
                
                nodes_info = nodes_df.to_string(index=False)
                return [TextContent(
                    type="text",
                    text=f"Nodes for project '{project}':\n{nodes_info}"
                )]
            
            else:
                return [TextContent(
                    type="text",
                    text=f"Unknown tool: {name}"
                )]
        
        except ConfigError as e:
            return [TextContent(
                type="text",
                text=f"Configuration error: {e}\nPlease check your .env file and database credentials."
            )]
        except DatabaseError as e:
            return [TextContent(
                type="text",
                text=f"Database error: {e}\nPlease check your VPN connection and database access."
            )]
        except RTGSLabToolsError as e:
            return [TextContent(
                type="text",
                text=f"Error: {e}"
            )]
        except Exception as e:
            logger.error(f"Unexpected error in tool {name}: {e}")
            return [TextContent(
                type="text",
                text=f"Unexpected error: {e}"
            )]
    
    return server


if __name__ == "__main__":
    # Set up logging
    setup_logging("INFO")
    
    # Create and run server
    server = create_server()
    
    # This would typically be run with: mcp run python -m rtgs_lab_tools.mcp_server.server
    import asyncio
    
    async def main():
        from mcp.server.stdio import stdio_server
        async with stdio_server() as streams:
            await server.run(*streams)
    
    asyncio.run(main())