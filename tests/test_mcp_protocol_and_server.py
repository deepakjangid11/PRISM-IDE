"""Tests for MCP Protocol Handler, JSON-RPC 2.0 Server, and Security Controls (Phase 24)."""

import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from prism.api.dependencies import mcp_service
from prism.api.main import app
from prism.llm.exceptions import LLMProviderError
from prism.llm.providers.mock_provider import MockLLMProvider
from prism.llm.schemas import LLMMessage, LLMRequest, LLMRole
from prism.llm.service import LLMService
from prism.mcp.protocol import MCPProtocolHandler
from prism.security.jwt import is_token_revoked, revoke_token
from prism.security.password import hash_password_argon2id, verify_password

client = TestClient(app)


@pytest.fixture
def protocol_handler() -> MCPProtocolHandler:
    return MCPProtocolHandler(mcp_service)


@pytest.mark.anyio
async def test_mcp_protocol_initialize(protocol_handler: MCPProtocolHandler) -> None:
    # 1. Supported protocol version negotiation
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }
    resp = await protocol_handler.handle_request(req)
    assert resp is not None
    assert resp["jsonrpc"] == "2.0"
    assert resp["id"] == 1
    assert "result" in resp
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "prism-mcp-server"
    assert "tools" in resp["result"]["capabilities"]

    # 2. Unsupported protocol version negotiating server supported version
    req_unsupported = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "initialize",
        "params": {
            "protocolVersion": "2023-01-01",
            "capabilities": {},
            "clientInfo": {"name": "legacy-client", "version": "0.1.0"},
        },
    }
    resp_unsupported = await protocol_handler.handle_request(req_unsupported)
    assert resp_unsupported is not None
    assert resp_unsupported["result"]["protocolVersion"] == "2024-11-05"

    # 3. Missing protocolVersion negotiating server supported version
    req_missing_version = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "initialize",
        "params": {},
    }
    resp_missing = await protocol_handler.handle_request(req_missing_version)
    assert resp_missing is not None
    assert resp_missing["result"]["protocolVersion"] == "2024-11-05"


@pytest.mark.anyio
async def test_mcp_protocol_ping_and_notifications(
    protocol_handler: MCPProtocolHandler,
) -> None:
    # 1. Normal ping request with ID returns a valid response
    ping_req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    resp = await protocol_handler.handle_request(ping_req)
    assert resp is not None
    assert resp["result"] == {}
    assert resp["id"] == 2

    # 2. notifications/initialized without ID is a valid notification and returns None
    notify_req = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    resp_notify = await protocol_handler.handle_request(notify_req)
    assert resp_notify is None

    # 3. Request containing "id": null is not silently treated as a valid notification
    null_id_req = {"jsonrpc": "2.0", "id": None, "method": "ping"}
    resp_null = await protocol_handler.handle_request(null_id_req)
    assert resp_null is not None
    assert resp_null["jsonrpc"] == "2.0"
    assert resp_null["id"] is None
    assert resp_null["result"] == {}

    # 4. notifications/initialized with "id": null is not silently treated as a valid notification
    null_id_notify = {
        "jsonrpc": "2.0",
        "id": None,
        "method": "notifications/initialized",
    }
    resp_null_notify = await protocol_handler.handle_request(null_id_notify)
    assert resp_null_notify is not None
    assert resp_null_notify["jsonrpc"] == "2.0"
    assert resp_null_notify["id"] is None
    assert resp_null_notify["result"] == {}

    # 5. Generic notification without ID returns None
    generic_notify = {"jsonrpc": "2.0", "method": "notifications/cancelled"}
    resp_generic = await protocol_handler.handle_request(generic_notify)
    assert resp_generic is None


@pytest.mark.anyio
async def test_mcp_protocol_tools_list(protocol_handler: MCPProtocolHandler) -> None:
    req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
    resp = await protocol_handler.handle_request(req)
    assert "result" in resp
    tools = resp["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    expected = [
        "get_developer_task",
        "read_project_file",
        "get_task_progress",
        "search_knowledge_docs",
        "submit_task_evaluation",
        "get_developer_report",
    ]
    for exp in expected:
        assert exp in tool_names

    # Check JSON Schema formatting
    read_tool = next(t for t in tools if t["name"] == "read_project_file")
    assert "inputSchema" in read_tool
    assert read_tool["inputSchema"]["type"] == "object"
    assert "file_path" in read_tool["inputSchema"]["properties"]
    assert "file_path" in read_tool["inputSchema"]["required"]


@pytest.mark.anyio
async def test_mcp_protocol_tools_call_read_project_file(
    protocol_handler: MCPProtocolHandler,
) -> None:
    req = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "read_project_file",
            "arguments": {"file_path": "README.md"},
        },
    }
    resp = await protocol_handler.handle_request(req)
    assert resp["result"]["isError"] is False
    content_text = resp["result"]["content"][0]["text"]
    assert "PRISM" in content_text


@pytest.mark.anyio
async def test_mcp_protocol_security_path_traversal(
    protocol_handler: MCPProtocolHandler,
) -> None:
    # 1. Path traversal attempt (outside workspace)
    req = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "read_project_file",
            "arguments": {"file_path": "../../some_outside_file.txt"},
        },
    }
    resp = await protocol_handler.handle_request(req)
    assert resp["result"]["isError"] is True
    assert "forbidden" in resp["result"]["content"][0]["text"].lower()

    # 2. Blocked pattern attempt (.env)
    req_env = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "read_project_file",
            "arguments": {"file_path": ".env"},
        },
    }
    resp_env = await protocol_handler.handle_request(req_env)
    assert resp_env["result"]["isError"] is True
    assert "restricted" in resp_env["result"]["content"][0]["text"].lower()

    # 3. Absolute volume path attempt (C:\Windows\win.ini)
    req_vol = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "read_project_file",
            "arguments": {"file_path": "C:\\Windows\\win.ini"},
        },
    }
    resp_vol = await protocol_handler.handle_request(req_vol)
    assert resp_vol["result"]["isError"] is True
    assert "volume" in resp_vol["result"]["content"][0]["text"].lower()


@pytest.mark.anyio
async def test_mcp_protocol_idor_developer_isolation(
    protocol_handler: MCPProtocolHandler,
) -> None:
    # Caller dev_a attempts to read progress for dev_b
    req = {
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "get_task_progress",
            "arguments": {"developer_id": "dev_victim_99"},
        },
    }
    resp = await protocol_handler.handle_request(req, caller_id="dev_attacker_01")
    assert resp["result"]["isError"] is True
    assert "Unauthorized" in resp["result"]["content"][0]["text"]


@pytest.mark.anyio
async def test_mcp_protocol_invalid_method_and_params(
    protocol_handler: MCPProtocolHandler,
) -> None:
    # Unknown method
    bad_req = {"jsonrpc": "2.0", "id": 9, "method": "non_existent_method"}
    resp = await protocol_handler.handle_request(bad_req)
    assert "error" in resp
    assert resp["error"]["code"] == -32601

    # Missing tools/call name
    bad_call = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {},
    }
    resp_call = await protocol_handler.handle_request(bad_call)
    assert "error" in resp_call
    assert resp_call["error"]["code"] == -32602


def test_fastapi_mcp_rpc_route() -> None:
    # 1. HTTP initialize request still returns 200
    init_payload = {
        "jsonrpc": "2.0",
        "id": 101,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }
    response = client.post("/mcp/rpc", json=init_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 101
    assert data["result"]["serverInfo"]["name"] == "prism-mcp-server"

    # 2. HTTP tools/list still returns all six registered tools
    list_payload = {"jsonrpc": "2.0", "id": 102, "method": "tools/list"}
    list_resp = client.post("/mcp/rpc", json=list_payload)
    assert list_resp.status_code == 200
    tools = list_resp.json()["result"]["tools"]
    assert len(tools) == 6

    # 3. HTTP notification without ID returns 202 Accepted with empty body
    notify_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
    }
    notify_resp = client.post("/mcp/rpc", json=notify_payload)
    assert notify_resp.status_code == 202
    assert notify_resp.text == ""
    assert len(notify_resp.content) == 0

    # 4. HTTP request with id: null returns 200 with JSON body
    null_id_payload = {
        "jsonrpc": "2.0",
        "id": None,
        "method": "ping",
    }
    null_resp = client.post("/mcp/rpc", json=null_id_payload)
    assert null_resp.status_code == 200
    null_data = null_resp.json()
    assert null_data["jsonrpc"] == "2.0"
    assert null_data["id"] is None
    assert null_data["result"] == {}


def test_stdio_server_notifications_and_requests() -> None:
    """Verify standard IO MCP server suppresses notification responses and keeps stdout clean."""
    proc = subprocess.Popen(
        [sys.executable, "src/prism/mcp/server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        # Send notification (no ID) - must produce NO stdout output
        notify_msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        proc.stdin.write(json.dumps(notify_msg) + "\n")

        # Send normal request (with ID) - must produce JSON response
        req_msg = {"jsonrpc": "2.0", "id": "req-ping-99", "method": "ping"}
        proc.stdin.write(json.dumps(req_msg) + "\n")
        proc.stdin.flush()

        # The first line on stdout must be the response to req-ping-99
        first_line = proc.stdout.readline()
        assert first_line, "Expected JSON-RPC response on stdout"
        parsed = json.loads(first_line)
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == "req-ping-99"
        assert parsed["result"] == {}

        # Send tools/list request
        list_msg = {"jsonrpc": "2.0", "id": "req-tools-1", "method": "tools/list"}
        proc.stdin.write(json.dumps(list_msg) + "\n")
        proc.stdin.flush()

        second_line = proc.stdout.readline()
        parsed_tools = json.loads(second_line)
        assert parsed_tools["id"] == "req-tools-1"
        assert len(parsed_tools["result"]["tools"]) == 6

    finally:
        if proc.stdin:
            proc.stdin.close()
        _, stderr_output = proc.communicate(timeout=5)

    # Logs remain on stderr and do not contaminate stdout
    assert "MCP client handshake initialized successfully" in stderr_output


@pytest.mark.anyio
async def test_llm_service_graceful_fallback() -> None:
    # Primary fails permanently
    primary = MockLLMProvider()
    primary.should_fail = True
    primary.failure_exception = LLMProviderError("Primary provider connection failed")

    # Fallback succeeds
    fallback = MockLLMProvider(default_response="Fallback provider answer")

    service = LLMService(provider=primary, fallback_provider=fallback)
    request = LLMRequest(
        messages=[LLMMessage(role=LLMRole.USER, content="Explain recursion")]
    )

    resp = await service.complete(request)
    assert resp.content == "Fallback provider answer"
    assert resp.provider == fallback.provider_type.value


def test_persistent_revocation_and_argon2id() -> None:
    # Test Argon2id
    pwd = "SecureArgonPassword123!"
    hashed_argon = hash_password_argon2id(pwd)
    assert hashed_argon.startswith("argon2id$")
    assert verify_password(pwd, hashed_argon) is True
    assert verify_password("WrongPassword!", hashed_argon) is False

    # Test persistent revocation
    test_jti = "test_jti_persistent_999"
    revoke_token(test_jti)
    assert is_token_revoked(test_jti) is True
