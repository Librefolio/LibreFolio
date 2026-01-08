#!/usr/bin/env python3
"""
API Endpoints utility script.

Usage:
    python list_api_endpoints.py              # List all endpoints (default)
    python list_api_endpoints.py --list       # List all endpoints
    python list_api_endpoints.py --openapi    # Export OpenAPI schema to stdout
    python list_api_endpoints.py --openapi-file [path]  # Export to file
"""
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app


def list_endpoints():
    """List all API endpoints with descriptions."""
    print('=' * 80)
    print('API ENDPOINTS')
    print('=' * 80)
    print()

    # Group routes by tag
    routes_by_tag = {}
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            # Get first line of docstring as description
            description = ''
            if route.endpoint and route.endpoint.__doc__:
                description = route.endpoint.__doc__.strip().split('\n')[0]

            # Get methods (exclude HEAD, OPTIONS)
            methods = [m for m in route.methods if m not in ['HEAD', 'OPTIONS']]

            # Get tags (or use 'default' if none)
            tags = getattr(route, 'tags', ['default'])
            for t in tags:
                if t not in routes_by_tag:
                    routes_by_tag[t] = []
                routes_by_tag[t].append({
                    'methods': methods,
                    'path': route.path,
                    'description': description
                    })

    # Print routes grouped by tag
    for tag in sorted(routes_by_tag.keys()):
        print(f'[{tag.upper()}]')
        print()

        for route in sorted(routes_by_tag[tag], key=lambda x: x['path']):
            methods_str = ', '.join(route['methods'])
            desc = route['description'] or '(no description)'

            # Format nicely
            print(f'  {methods_str:<10} {route["path"]:<50} {desc}')

        print()

    print('=' * 80)
    print(f'Total endpoints: {len(app.routes)}')
    print('=' * 80)


def export_openapi(output_path: str | None = None):
    """Export OpenAPI schema to file or stdout."""
    openapi_schema = app.openapi()

    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(openapi_schema, f, indent=2)
        print(f"OpenAPI schema exported to: {output_file}")
        return str(output_file)
    else:
        print(json.dumps(openapi_schema, indent=2))
        return None


def main():
    parser = argparse.ArgumentParser(
        description='API Endpoints utility script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python list_api_endpoints.py                    # List all endpoints
  python list_api_endpoints.py --openapi          # Print OpenAPI to stdout
  python list_api_endpoints.py --openapi-file frontend/src/lib/api/openapi.json
        """
    )

    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all API endpoints with descriptions'
    )
    parser.add_argument(
        '--openapi', '-o',
        action='store_true',
        help='Export OpenAPI schema to stdout'
    )
    parser.add_argument(
        '--openapi-file', '-f',
        type=str,
        metavar='PATH',
        help='Export OpenAPI schema to file'
    )

    args = parser.parse_args()

    # Default action is to list endpoints
    if not any([args.list, args.openapi, args.openapi_file]):
        args.list = True

    if args.list:
        list_endpoints()

    if args.openapi:
        export_openapi()

    if args.openapi_file:
        export_openapi(args.openapi_file)


if __name__ == '__main__':
    main()

