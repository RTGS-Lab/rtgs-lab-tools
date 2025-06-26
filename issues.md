## Issues

-Need to verify that all tools work. Go one by one recursively through the --help and verify output of each tool

**Analysis**: This is a comprehensive testing issue requiring systematic validation of all CLI tools. The testing needs to verify both help text accuracy and actual functionality of each tool and subcommand.

**Scope**: Would involve creating a test script that iterates through all CLI entry points, executes `--help` for each tool/subcommand, and validates that the output matches expected behavior. Also requires functional testing of each tool's core operations.

**Effort**: Medium - Requires systematic approach but relatively straightforward execution. Could be automated with a test script.

---

-Need to split up mcp servers into multiple servers, one for each tool. Curent file is too large

**Analysis**: The current MCP server configuration appears to be monolithic, making it difficult to maintain and potentially causing performance issues. Each tool should have its own dedicated MCP server instance.

**Scope**: Requires refactoring the MCP server architecture to create individual server files for each tool (audit, data_parser, device_configuration, etc.) and updating the server registration/discovery mechanism.

**Effort**: Medium-High - Architectural change requiring careful planning to avoid breaking existing integrations. Need to ensure each server can run independently and maintain backward compatibility.

---

-Need to verify each cli isnt doing too much business logic. Tools should push out there functions into specific files and the cli should use those. This enables downstream tools to use the functions directly by importing rather than using the cli

**Analysis**: This is a separation of concerns issue where CLI modules contain business logic that should be extracted into separate core modules. This limits reusability and makes testing more difficult.

**Scope**: Requires refactoring each CLI module to move business logic into dedicated core modules (e.g., moving logic from `cli.py` files into `core.py` or specific functional modules). CLI should become thin wrappers around these core functions.

**Effort**: High - Requires systematic refactoring of multiple modules. Each tool needs analysis to identify what logic should be extracted and careful testing to ensure functionality is preserved.

---

-each module should have a detailed documentaiton file that descirbes example uses of the tool, as well as what every parameter does

**Analysis**: Documentation gaps exist across the codebase. Each module lacks comprehensive documentation explaining usage patterns, parameter descriptions, and practical examples.

**Scope**: Create detailed documentation files (likely README.md or docs/ files) for each module explaining: purpose, installation, usage examples, parameter descriptions, common use cases, and troubleshooting.

**Effort**: Medium - Primarily documentation work, but requires deep understanding of each tool's functionality and common usage patterns. Time-consuming but straightforward.

---

-the audit reproduce tool currently does not produce a runnable script because of file naming from reproduced tool calls

**Analysis**: The audit reproduce functionality has a bug where it generates scripts with incorrect file names or paths, making the reproduced scripts non-executable.

**Scope**: Debug the audit reproduce tool's file naming logic, likely in the script generation code. Need to ensure generated scripts have proper file names and executable permissions.

**Effort**: Low-Medium - Specific bug fix requiring investigation of the audit reproduce code path and fixing the file naming logic.

---

-need to integrate device monitor tool - it should also be command line based so that it can be wrapped in mcp server

**Analysis**: A device monitor tool exists but is not integrated into the CLI framework. It needs to be converted to use the standard CLI patterns and integrated into the MCP server architecture.

**Scope**: Convert the device monitor tool to use the CLI utilities framework, ensure it follows the same patterns as other tools, and integrate it into the MCP server configuration.

**Effort**: Medium - Requires understanding the existing device monitor functionality and adapting it to fit the established CLI patterns. Integration work rather than new development.

---


-postgres logging should use core database manager class to connect

**Analysis**: The PostgreSQL logger is currently using its own connection management instead of leveraging the existing core database manager class, leading to code duplication and inconsistent connection handling.

**Scope**: Refactor the PostgreSQL logger to use the core database manager class for connections. This requires updating the logger initialization and ensuring compatibility with the existing database manager interface.

**Effort**: Medium - Requires refactoring the logger to use shared database connection management while maintaining all existing functionality.

---

-error parsing should be worked on so it works

**Analysis**: The error parsing functionality appears to be broken or incomplete. This likely affects the system's ability to properly parse and categorize errors from tool executions.

**Scope**: Investigate the error parsing code, identify what's broken, and fix the parsing logic. May require updating error message formats or parsing patterns.

**Effort**: Low-Medium - Debugging and fixing existing functionality. Effort depends on the extent of the issues in the error parsing logic.

---

-data/metadata/diagnostics parsers should be updated so multi indexed data like PORT_V and PORT_I are broken out

**Analysis**: The data parsers are not properly handling multi-indexed data structures. Data like PORT_V and PORT_I (which likely have multiple indices/channels) are being treated as single entities instead of being broken out into their component parts.

**Scope**: Update the parsing logic to properly handle multi-indexed data structures. This likely involves updating the data parsing rules to recognize and separate indexed data into individual components.

**Effort**: Medium - Requires understanding the data structure patterns and updating parsing logic. May require changes to data storage schema as well.

---

-extract tool BETWEEN query is not inclusive of current time, should get data through current time instead of stopping at 00:00:00 of current day

**Analysis**: The extract tool's BETWEEN query has a time inclusivity issue where it only extracts data up to the start of the current day (00:00:00) rather than including data through the current time. This results in incomplete data extraction when running the tool during the day.

**Scope**: Update the BETWEEN query logic in the extract tool to use the current timestamp instead of just the current date at 00:00:00. This ensures all available data up to the moment of extraction is included.

**Effort**: Low - Simple query modification to change the end time from current date at midnight to current timestamp. Requires updating the SQL query generation logic.

---

-implement GCP authorization for Google Cloud PostgreSQL connection instead of IP whitelisting

**Analysis**: The current Google Cloud PostgreSQL connection relies on IP whitelisting for access control, which is less secure and harder to manage than proper GCP authorization mechanisms. This creates security risks and operational overhead when IP addresses change.

**Scope**: Implement Cloud SQL Auth Proxy or IAM database authentication to replace IP whitelisting. This involves setting up service accounts, configuring IAM roles, updating connection strings to use GCP authentication, and testing connectivity across all environments.

**Effort**: Medium - Requires GCP service account setup, IAM configuration, code changes to use GCP authentication libraries, and thorough testing. May need to handle different authentication methods for different deployment scenarios. 