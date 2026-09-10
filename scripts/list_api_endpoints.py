#!/usr/bin/env python3
"""
API Endpoints utility script.

Usage:
    python list_api_endpoints.py              # List all endpoints (default)
    python list_api_endpoints.py --list       # List all endpoints
    python list_api_endpoints.py --openapi    # Export OpenAPI schema to stdout
    python list_api_endpoints.py --openapi-file [path]  # Export to file
    python list_api_endpoints.py --tool-contracts-file [path]  # Schema-only Tool export
"""
import argparse
import json
import sys
from pathlib import Path

# Add project root to path (file is in scripts/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def list_endpoints():
    """List all API endpoints with descriptions."""
    from backend.app.main import app  # noqa: PLC0415 — schema-only Tool exports must not import the application

    schema = app.openapi()
    print("=" * 80)
    print("API ENDPOINTS")
    print("=" * 80)
    print()

    # Group routes by tag
    routes_by_tag = {}
    endpoint_count = 0
    for path, path_item in schema.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} or not isinstance(operation, dict):
                continue
            endpoint_count += 1
            description = operation.get("summary") or str(operation.get("description", "")).strip().split("\n")[0]
            for tag in operation.get("tags") or ["default"]:
                routes_by_tag.setdefault(tag, []).append(
                    {"methods": [method.upper()], "path": path, "description": description}
                )

    # Print routes grouped by tag
    for tag in sorted(routes_by_tag.keys()):
        print(f"[{tag.upper()}]")
        print()

        for route in sorted(routes_by_tag[tag], key=lambda x: x["path"]):
            methods_str = ", ".join(route["methods"])
            desc = route["description"] or "(no description)"

            # Format nicely
            print(f'  {methods_str:<10} {route["path"]:<50} {desc}')

        print()

    print("=" * 80)
    print(f"Total endpoints: {endpoint_count}")
    print("=" * 80)


def export_openapi(output_path: str | None = None):
    """Export OpenAPI schema to file or stdout."""
    from backend.app.main import app  # noqa: PLC0415 — schema-only Tool exports must not import the application

    openapi_schema = app.openapi()

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(openapi_schema, f, indent=2)
        print(f"OpenAPI schema exported to: {output_file}")
        return str(output_file)
    else:
        print(json.dumps(openapi_schema, indent=2))
        return None


def main():
    parser = argparse.ArgumentParser(
        description="API Endpoints utility script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python list_api_endpoints.py                    # List all endpoints
  python list_api_endpoints.py --openapi          # Print OpenAPI to stdout
  python list_api_endpoints.py --openapi-file frontend/src/lib/api/openapi.json
  python list_api_endpoints.py --tool-contracts-file frontend/src/lib/api/tool-contracts.openapi.json
        """,
        )

    parser.add_argument(
        "--list", "-l", action="store_true", help="List all API endpoints with descriptions"
        )
    parser.add_argument(
        "--openapi", "-o", action="store_true", help="Export OpenAPI schema to stdout"
        )
    parser.add_argument(
        "--openapi-file", "-f", type=str, metavar="PATH", help="Export OpenAPI schema to file"
        )
    parser.add_argument(
        "--tool-contracts-file", type=str, metavar="PATH",
        help="Export schema-only Tool contracts without importing the API application"
        )

    args = parser.parse_args()

    # Default action is to list endpoints
    if not any([args.list, args.openapi, args.openapi_file, args.tool_contracts_file]):
        args.list = True

    if args.list:
        list_endpoints()

    if args.openapi:
        export_openapi()

    if args.openapi_file:
        export_openapi(args.openapi_file)

    if args.tool_contracts_file:
        from scripts.export_tool_contracts import export_tool_contracts  # noqa: PLC0415 — load Tool export support only for its explicit action

        output = export_tool_contracts(args.tool_contracts_file)
        print(f"Tool contracts exported to: {output}")


if __name__ == "__main__":
    main()
