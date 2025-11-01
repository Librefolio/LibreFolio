"""
CHECK Constraints Hook for Alembic

SQLite limitation: Alembic autogenerate doesn't detect CHECK constraints via reflection.
This hook verifies that all CHECK constraints defined in SQLModel models exist in the database,
and adds them if missing.

Usage:
  Can be run standalone: python -m backend.alembic.check_constraints_hook
  Or imported and called after migration: check_and_add_missing_constraints()

Author: LibreFolio Contributors
"""
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from sqlalchemy import CheckConstraint, inspect, text
from sqlmodel import Session

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db import engine
from backend.app.db.base import SQLModel


def get_model_check_constraints() -> Dict[str, List[Tuple[str, str]]]:
    """
    Extract CHECK constraints from SQLModel models.

    Returns:
        Dict mapping table_name -> [(constraint_name, constraint_sql), ...]
    """
    constraints = {}

    for table_name, table in SQLModel.metadata.tables.items():
        check_constraints = []

        # Get CHECK constraints from table
        for constraint in table.constraints:
            if isinstance(constraint, CheckConstraint):
                constraint_name = constraint.name
                # Get SQL expression as string
                constraint_sql = str(constraint.sqltext)
                check_constraints.append((constraint_name, constraint_sql))

        if check_constraints:
            constraints[table_name] = check_constraints

    return constraints


def get_db_check_constraints(table_name: str) -> List[str]:
    """
    Get CHECK constraints from database for a specific table (SQLite).

    Args:
        table_name: Name of the table

    Returns:
        List of constraint SQL expressions found in CREATE TABLE statement
    """
    with Session(engine) as session:
        # Query sqlite_master for table definition
        result = session.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:table_name"),
            {"table_name": table_name}
        ).first()

        if not result or not result[0]:
            return []

        create_sql = result[0]

        # Parse CHECK constraints from CREATE TABLE
        # Look for "CHECK (...)" or "CONSTRAINT name CHECK (...)"
        import re
        check_pattern = r'(?:CONSTRAINT\s+\w+\s+)?CHECK\s*\(([^)]+)\)'
        matches = re.findall(check_pattern, create_sql, re.IGNORECASE)

        return matches


def add_check_constraint_to_table(table_name: str, constraint_name: str, constraint_sql: str) -> bool:
    """
    Add CHECK constraint to table by recreating it (SQLite doesn't support ALTER TABLE ADD CONSTRAINT for CHECK).

    Args:
        table_name: Table name
        constraint_name: Constraint name
        constraint_sql: Constraint SQL expression

    Returns:
        True if successfully added, False otherwise
    """
    print(f"⚠️  SQLite doesn't support ALTER TABLE ADD CONSTRAINT for CHECK constraints.")
    print(f"   To add constraint '{constraint_name}' to '{table_name}':")
    print(f"   1. Create a new migration with Alembic")
    print(f"   2. Manually add the constraint in the migration:")
    print(f"      op.execute('''")
    print(f"          ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} CHECK ({constraint_sql})")
    print(f"      ''')")
    print(f"   OR recreate the table with the constraint included.")
    print()
    return False


def check_and_add_missing_constraints(auto_fix: bool = False, verbose: bool = True) -> Tuple[bool, List[str]]:
    """
    Check if all CHECK constraints from models exist in database.

    Args:
        auto_fix: If True, attempt to add missing constraints (limited on SQLite)
        verbose: If True, print detailed output

    Returns:
        Tuple of (all_present, missing_constraints_list)
    """
    if verbose:
        print("=" * 70, flush=True)
        print("CHECK Constraints Verification", flush=True)
        print("=" * 70, flush=True)
        print(flush=True)

    model_constraints = get_model_check_constraints()
    missing = []

    for table_name, constraints in model_constraints.items():
        if verbose:
            print(f"📋 Table: {table_name}")

        db_constraints = get_db_check_constraints(table_name)

        for constraint_name, constraint_sql in constraints:
            # Normalize SQL for comparison (remove extra spaces, case-insensitive)
            normalized_expected = constraint_sql.strip().lower().replace(" ", "")

            found = False
            for db_constraint in db_constraints:
                normalized_db = db_constraint.strip().lower().replace(" ", "")
                if normalized_expected == normalized_db:
                    found = True
                    break

            if found:
                if verbose:
                    print(f"  ✅ {constraint_name}: {constraint_sql}")
            else:
                if verbose:
                    print(f"  ❌ {constraint_name}: {constraint_sql} - MISSING")
                missing.append(f"{table_name}.{constraint_name}")

                if auto_fix:
                    add_check_constraint_to_table(table_name, constraint_name, constraint_sql)

        if verbose:
            print()

    if missing:
        if verbose:
            print(f"⚠️  Found {len(missing)} missing CHECK constraint(s)")
            print("   These constraints are defined in models but not in database.")
            print()
            print("🔧 HOW TO FIX:")
            print()
            print("STEP 1: Find the migration file")
            print("  Look in: backend/alembic/versions/")
            print("  Check the most recent migration or the one that created this table")
            print()
            print("STEP 2: Add the CHECK constraint to the migration")
            print("  Edit the upgrade() function and add:")
            print()

            # Print concrete code examples for each missing constraint
            for table_constraint in missing:
                table_name, constraint_name = table_constraint.rsplit('.', 1)
                # Find the constraint SQL
                for tbl, constraints in model_constraints.items():
                    if tbl == table_name:
                        for cname, csql in constraints:
                            if cname == constraint_name:
                                print(f"  # For {table_name}.{constraint_name}")
                                print(f"  with op.batch_alter_table('{table_name}', schema=None) as batch_op:")
                                print(f"      batch_op.create_check_constraint(")
                                print(f"          '{constraint_name}',")
                                print(f"          '{csql}'")
                                print(f"      )")
                                print()

            print("STEP 3: Apply the fix")
            print("  If migration already applied (most common):")
            print("    1. ./dev.sh db:downgrade")
            print("    2. Edit the migration file as shown above")
            print("    3. ./dev.sh db:upgrade")
            print()
            print("  If migration NOT yet applied:")
            print("    1. Edit the migration file as shown above")
            print("    2. ./dev.sh db:upgrade")
            print()
            print("📚 See: docs/alembic-guide.md (SQLite CHECK Constraints section)")
            print()
        return False, missing
    else:
        if verbose:
            print("✅ All CHECK constraints are present in database")
            print()
        return True, []


def main():
    """Run CHECK constraints verification."""
    import argparse

    # Force unbuffered output
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

    try:
        parser = argparse.ArgumentParser(description="Verify CHECK constraints in database")
        parser.add_argument("--fix", action="store_true", help="Attempt to add missing constraints")
        parser.add_argument("--quiet", action="store_true", help="Minimal output")

        args = parser.parse_args()

        all_present, missing = check_and_add_missing_constraints(
            auto_fix=args.fix,
            verbose=not args.quiet
        )

        if not all_present:
            sys.exit(1)

        sys.exit(0)

    except Exception as e:
        print(f"❌ Error running CHECK constraints verification: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

