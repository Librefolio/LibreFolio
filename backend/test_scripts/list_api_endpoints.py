#!/usr/bin/env python3
"""
List all API endpoints with their descriptions.
"""
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app

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

        # Get tags (or use 'default' if none)
        tags = getattr(route, 'tags', ['default'])
        tag = tags[0] if tags else 'default'

        if tag not in routes_by_tag:
            routes_by_tag[tag] = []

        # Get methods (exclude HEAD, OPTIONS)
        methods = [m for m in route.methods if m not in ['HEAD', 'OPTIONS']]

        routes_by_tag[tag].append({
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
print(f'Total endpoints: {sum(len(routes) for routes in routes_by_tag.values())}')
print('=' * 80)
