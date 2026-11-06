import json

from prism.api.main import app


def discover():
    routes = []
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    print(f"Total OpenAPI Paths: {len(paths)}")
    total_endpoints = 0

    for path, methods in sorted(paths.items()):
        for method, details in sorted(methods.items()):
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "options",
                "head",
            }:
                continue
            total_endpoints += 1
            op_id = details.get("operationId", "")
            summary = details.get("summary", "")
            tags = details.get("tags", [])
            security = details.get("security", [])
            req_body = details.get("requestBody", {})
            responses = list(details.get("responses", {}).keys())

            routes.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": op_id,
                    "summary": summary,
                    "tags": tags,
                    "security": security,
                    "has_request_body": bool(req_body),
                    "responses": responses,
                }
            )

    print(f"Total Discovered Endpoint Operations: {total_endpoints}")
    with open("docs/api_inventory.json", "w", encoding="utf-8") as f:
        json.dump(routes, f, indent=2)
    print("Exported inventory to docs/api_inventory.json")

    # Group by Tag
    by_tag = {}
    for r in routes:
        t = r["tags"][0] if r["tags"] else "Uncategorized"
        by_tag.setdefault(t, []).append(r)

    for tag, group in sorted(by_tag.items()):
        print(f"\n### {tag} ({len(group)} endpoints)")
        for r in group:
            sec = "[AUTH]" if r["security"] else ""
            print(f"  - {r['method']:<6} {r['path']} {sec} ({r['operation_id']})")


if __name__ == "__main__":
    discover()
