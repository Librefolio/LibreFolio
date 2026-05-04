#!/usr/bin/env python3
"""Allow running as: python -m scripts.test_runner [args]"""

import sys
import traceback

from ._common import Colors
from ._cli import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Test execution interrupted by user{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.NC}")
        traceback.print_exc()
        sys.exit(1)

