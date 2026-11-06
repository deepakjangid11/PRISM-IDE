"""Postman Collection and Environment Generator for PRISM IDE.

Generates:
1. docs/prism_api_postman_collection.json (v2.1.0 formatted with 17 functional folders, authentication, variables)
2. docs/prism_postman_environment.json (environment variables: base_url, access_token, developer_id, task_id, etc.)
"""

from __future__ import annotations

import json
from pathlib import Path

from prism.api.main import app


def generate_postman_artifacts() -> None:
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    # Organize by primary tag
    folders: dict[str, list[dict]] = {}

    for path, methods in sorted(paths.items()):
        for method, op in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete"}:
                continue

            tags = op.get("tags", ["General"])
            tag = tags[0] if tags else "General"
            if tag not in folders:
                folders[tag] = []

            # Format URL
            url_path = path.lstrip("/")
            # Convert {param} to :param for Postman
            postman_path = url_path
            path_segments = [
                p.replace("{", ":").replace("}", "") for p in url_path.split("/")
            ]

            # Query params
            query_items = []
            for param in op.get("parameters", []):
                if param.get("in") == "query":
                    query_items.append(
                        {
                            "key": param["name"],
                            "value": str(param.get("schema", {}).get("default", "")),
                            "description": param.get("description", ""),
                            "disabled": not param.get("required", False),
                        }
                    )

            # Headers
            headers = [
                {"key": "Content-Type", "value": "application/json"},
                {"key": "Authorization", "value": "Bearer {{access_token}}"},
            ]

            # Request Body
            body_obj = None
            if "requestBody" in op:
                body_schema = (
                    op["requestBody"]
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                )
                ref = body_schema.get("$ref")
                sample_data = {}
                if ref:
                    schema_name = ref.split("/")[-1]
                    schema_def = (
                        openapi.get("components", {})
                        .get("schemas", {})
                        .get(schema_name, {})
                    )
                    props = schema_def.get("properties", {})
                    for p_name, p_val in props.items():
                        p_type = p_val.get("type", "string")
                        if p_type == "string":
                            sample_data[p_name] = p_val.get(
                                "default", f"sample_{p_name}"
                            )
                        elif p_type == "integer":
                            sample_data[p_name] = p_val.get("default", 1)
                        elif p_type == "number":
                            sample_data[p_name] = p_val.get("default", 1.0)
                        elif p_type == "boolean":
                            sample_data[p_name] = p_val.get("default", True)
                        elif p_type == "array":
                            sample_data[p_name] = p_val.get("default", [])
                        elif p_type == "object":
                            sample_data[p_name] = p_val.get("default", {})
                body_obj = {
                    "mode": "raw",
                    "raw": json.dumps(sample_data, indent=2),
                    "options": {"raw": {"language": "json"}},
                }

            item = {
                "name": op.get("summary") or f"{method.upper()} {path}",
                "request": {
                    "method": method.upper(),
                    "header": headers,
                    "url": {
                        "raw": "{{base_url}}/" + postman_path,
                        "host": ["{{base_url}}"],
                        "path": path_segments,
                        "query": query_items,
                    },
                    "description": op.get("description", ""),
                },
                "response": [],
            }
            if body_obj:
                item["request"]["body"] = body_obj

            folders[tag].append(item)

    # Build collection items
    collection_items = []
    for tag_name, items in sorted(folders.items()):
        collection_items.append(
            {
                "name": tag_name,
                "item": items,
            }
        )

    collection = {
        "info": {
            "_postman_id": "prism-ide-api-collection-2026",
            "name": "PRISM IDE — Developer Intelligence & Learning Platform API",
            "description": "Complete production API suite for PRISM (Personalized Real-time Intelligent Skill Mentor). Includes Auth, Activity Intelligence, Skill Tracking, Tasks, Progressive Mentoring Dialogues, AST Evaluation, RAG Code Search, MCP Tools, Progress Analytics, and Reports.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": collection_items,
    }

    # Environment
    environment = {
        "id": "prism-ide-environment-local",
        "name": "PRISM IDE — Local Environment",
        "values": [
            {
                "key": "base_url",
                "value": "http://127.0.0.1:8000",
                "type": "default",
                "enabled": True,
            },
            {"key": "access_token", "value": "", "type": "secret", "enabled": True},
            {"key": "refresh_token", "value": "", "type": "secret", "enabled": True},
            {
                "key": "developer_id",
                "value": "dev_local_001",
                "type": "default",
                "enabled": True,
            },
            {"key": "task_id", "value": "tsk_001", "type": "default", "enabled": True},
            {
                "key": "submission_id",
                "value": "sub_001",
                "type": "default",
                "enabled": True,
            },
            {
                "key": "conversation_id",
                "value": "conv_001",
                "type": "default",
                "enabled": True,
            },
            {
                "key": "report_id",
                "value": "rep_001",
                "type": "default",
                "enabled": True,
            },
        ],
        "_postman_variable_scope": "environment",
    }

    out_coll = Path("docs/prism_api_postman_collection.json")
    out_env = Path("docs/prism_postman_environment.json")
    out_coll.parent.mkdir(parents=True, exist_ok=True)

    with open(out_coll, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)

    with open(out_env, "w", encoding="utf-8") as f:
        json.dump(environment, f, indent=2)

    print(
        f"Postman Collection generated at: {out_coll.resolve()} ({len(collection_items)} folders, {sum(len(f['item']) for f in collection_items)} endpoints)"
    )
    print(f"Postman Environment generated at: {out_env.resolve()}")


if __name__ == "__main__":
    generate_postman_artifacts()
