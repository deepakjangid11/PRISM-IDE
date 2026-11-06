# PRISM — Model Context Protocol (MCP) Server Documentation

**Protocol Specification:** Model Context Protocol (MCP) `2024-11-05`
**Server Name:** `prism-mcp-server`
**Server Version:** `0.1.0`
**Transports Supported:** Standard Stdio (CLI / IDEs) & JSON-RPC 2.0 over HTTP (`POST /mcp/rpc`)

---

## 1. Overview & Connection Architecture

PRISM includes an official Model Context Protocol server that allows external AI assistants (such as Claude Desktop, Cursor, and Antigravity) to safely inspect project code, access assigned coding tasks, evaluate work submissions, and search documentation.

```
+-----------------------------------------------------------------------------------+
|                            MCP Client (AI Assistant)                              |
+-----------------------------------------------------------------------------------+
         |                                                 |
         | (1) Standard Stdio (Line-delimited JSON-RPC)     | (2) HTTP POST /mcp/rpc
         v                                                 v
+-----------------------------------------------------------------------------------+
|                         PRISM MCP Protocol Dispatcher                             |
|                           (src/prism/mcp/protocol.py)                             |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            PRISM MCP Service & Tools                              |
|                            (src/prism/mcp/service.py)                             |
|                                                                                   |
|  [get_developer_task]     [read_project_file]       [get_task_progress]           |
|  [search_knowledge_docs]  [submit_task_evaluation]  [get_developer_report]        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                       Security Guards & Audit Logger                              |
| - Path Traversal Denial     - Blocked Patterns (.env)    - Caller Ownership Auth  |
| - 1 MB File Read Limit      - Volume Prefix Denial       - MySQL Audit Logging    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Connecting to PRISM MCP Server

### 2.1 Claude Desktop Configuration
Add the following to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "prism": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\HP\\Downloads\\PRISM IDE",
        "run",
        "python",
        "-m",
        "prism.mcp.server"
      ]
    }
  }
}
```

### 2.2 HTTP JSON-RPC 2.0 Endpoint
Connect over HTTP by sending POST requests to `http://localhost:8000/mcp/rpc`.

---

## 3. Registered Tool Catalog & Schemas

### 3.1 `get_developer_task`
- **Description:** Retrieve complete task details, requirements, acceptance criteria, and progressive hints.
- **Parameters:**
  - `task_id` (string, required): Unique task identifier.

### 3.2 `read_project_file`
- **Description:** Read an authorized project source file within workspace boundaries.
- **Parameters:**
  - `file_path` (string, required): Relative path of file to read.
- **Security Constraints:** Rejects path traversal (`..`), absolute Windows volumes (`C:\`), and blocked patterns (`.env`, `.git`, `.venv`, `password`, `secret`). Limit: 1 MB.

### 3.3 `get_task_progress`
- **Description:** Retrieve task progression, counts, and completion statuses for a developer.
- **Parameters:**
  - `developer_id` (string, required): Developer identifier.
- **Security:** Enforces caller ownership check (`caller_id == developer_id`).

### 3.4 `search_knowledge_docs`
- **Description:** Search authorized programming, architectural, and learning documentation via RAG.
- **Parameters:**
  - `query` (string, required): Semantic query.
  - `top_k` (integer, optional, default: 3): Number of results (1-10).

### 3.5 `submit_task_evaluation`
- **Description:** Trigger automated static analysis and acceptance criteria evaluation for a task submission.
- **Parameters:**
  - `submission_id` (string, required): Unique submission identifier.

### 3.6 `get_developer_report`
- **Description:** Retrieve or generate a comprehensive periodic performance and learning report.
- **Parameters:**
  - `developer_id` (string, required): Developer identifier.
  - `period_type` (string, optional, default: "weekly"): "daily", "weekly", or "monthly".
- **Security:** Enforces caller ownership check.

---

## 4. MCP JSON-RPC 2.0 Protocol Examples

### Handshake (`initialize`)
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "claude-client", "version": "1.0.0"}
  }
}
```

### Response
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {"listChanged": false},
      "logging": {}
    },
    "serverInfo": {
      "name": "prism-mcp-server",
      "version": "0.1.0"
    }
  }
}
```

### Call Tool (`tools/call`)
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "read_project_file",
    "arguments": {"file_path": "README.md"}
  }
}
```

### Response
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "# PRISM IDE — AI-powered developer intelligence..."
      }
    ],
    "isError": false
  }
}
```
