# MCP Server

TripAgent provides a Model Context Protocol (MCP) server that exposes read tools to MCP clients (such as Claude Desktop or Claude Code). Write tools are exposed, but return a structured rejection message indicating that write actions require the human approval queue.

## Configuration

Add the following to your `claude_desktop_config.json` (or equivalent configuration file for your MCP client):

```json
{
  "mcpServers": {
    "tripagent": {
      "command": "uv",
      "args": [
        "run",
        "mcp_server/server.py"
      ],
      "cwd": "/path/to/TripAgent"
    }
  }
}
```

Be sure to replace `/path/to/TripAgent` with the actual absolute path to the repository.

## Capabilities

The server uses the `stdio` transport to communicate with the client.

It iterates through the `ToolRegistry` and exposes:
1. **Read Tools:** Directly executable, returning exact outputs.
2. **Write Tools:** Rejects execution programmatically to maintain safety boundaries. Write tools MUST be routed through the TripAgent Approval Queue via the normal web interface.
