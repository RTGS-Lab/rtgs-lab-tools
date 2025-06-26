## Issues

-Need to verify that all tools work. Go one by one recursively through the --help and verify output of each tool
-Need to split up mcp servers into multiple servers, one for each tool. Curent file is too large
-Need to verify each cli isnt doing too much business logic. Tools should push out there functions into specific files and the cli should use those. This enables downstream tools to use the functions directly by importing rather than using the cli
-each module should have a detailed documentaiton file that descirbes example uses of the tool, as well as what every parameter does
-the audit reproduce tool currently does not produce a runnable script because of file naming from reproduced tool calls
-need to integrate device monitor tool - it should also be command line based so that it can be wrapped in mcp server
-postgres needs to be migrated to google cloud instance rather than rtgs-test local db
