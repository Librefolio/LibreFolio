# Alembic Database Migrations - Simple Guide

## 🤔 What is Alembic?

**Alembic** is a database migration tool for SQLAlchemy/SQLModel. Think of it as "version control for your database schema".

**Why do we need it?**
- Your database structure changes as you develop (add tables, modify columns, etc.)
- You need a way to apply these changes safely
- You need to track what changes were made and when
- You need to be able to rollback if something goes wrong

---

## 📁 Where Are Migrations Stored?

```
LibreFolio/
└── backend/
    ├── alembic/
    │   ├── versions/           ← Migration files live here
    │   │   └── 37d14b3d7a82_initial_schema.py
    │   ├── env.py              ← Alembic configuration
    │   └── script.py.mako      ← Template for new migrations
    ├── alembic.ini             ← Alembic settings
    └── data/
        └── sqlite/
            └── app.db          ← Your actual database
```

**Key locations:**
- `backend/alembic/versions/` - All migration files (like git commits)
- `backend/data/sqlite/app.db` - Your database with an `alembic_version` table tracking which migrations are applied

---

## 🔧 The 4 Essential Commands

### 1. `./dev.sh db:current` - "Where am I?"

**What it does:**
Shows which migration is currently applied to your database.

**Example output:**
```bash
$ ./dev.sh db:current
37d14b3d7a82 (head)
```

**When to use:**
- Check if your database is up-to-date
- Verify which version is running
- Debug migration issues

**What happens internally:**
1. Checks the `alembic_version` table in your database
2. Shows the revision ID of the last applied migration
3. `(head)` means you're on the latest migration

---

### 2. `./dev.sh db:migrate "message"` - "I changed something, save it!"

**What it does:**
Creates a NEW migration file based on changes you made to your models.

**Example:**
```bash
# You added a new column to Asset model
$ ./dev.sh db:migrate "add notes column to assets"

# Alembic creates:
backend/alembic/versions/abc123def456_add_notes_column_to_assets.py
```

**When to use:**
- After modifying any model in `backend/app/db/models.py`
- Before committing your code changes

**What happens internally:**
1. Alembic compares your **models.py** with your **database**
2. Detects differences (new tables, columns, etc.)
3. Generates Python code to apply those changes
4. Saves it in `backend/alembic/versions/`

**⚠️ Important:**
- The migration is **created** but NOT applied yet
- You need to run `db:upgrade` to apply it
- Always review the generated migration file!

**Example migration file:**
```python
def upgrade() -> None:
    # Add column 'notes' to 'assets' table
    op.add_column('assets', sa.Column('notes', sa.Text(), nullable=True))

def downgrade() -> None:
    # Remove column 'notes' from 'assets' table
    op.drop_column('assets', 'notes')
```

---

### 3. `./dev.sh db:upgrade` - "Apply all pending changes!"

**What it does:**
Applies all migrations that haven't been applied yet to your database.

**Example:**
```bash
$ ./dev.sh db:upgrade

INFO  [alembic.runtime.migration] Running upgrade  -> 37d14b3d7a82, Initial schema
INFO  [alembic.runtime.migration] Running upgrade 37d14b3d7a82 -> abc123def456, add notes column
```

**When to use:**
- After pulling code with new migrations
- After creating a new migration with `db:migrate`
- When setting up a fresh environment
- **Always** after creating a new migration!

**What happens internally:**
1. Checks `alembic_version` table to see current version
2. Finds all migrations between current and `head` (latest)
3. Executes `upgrade()` function in each migration file
4. Updates database schema
5. Updates `alembic_version` table

**Real-world example:**
```bash
# Teammate adds new table
git pull

# You need to update your database
./dev.sh db:upgrade

# Now your database matches the code
./dev.sh server  # Server starts successfully
```

---

### 4. `./dev.sh db:downgrade` - "Oops, undo the last change!"

**What it does:**
Rolls back the LAST applied migration (one step back).

**Example:**
```bash
$ ./dev.sh db:downgrade

INFO  [alembic.runtime.migration] Running downgrade abc123def456 -> 37d14b3d7a82
```

**When to use:**
- You applied a migration that broke something
- You want to test the downgrade path
- You need to go back to a previous state

**What happens internally:**
1. Finds the current migration
2. Executes the `downgrade()` function
3. Reverts the database changes
4. Updates `alembic_version` table to previous revision

**⚠️ Warning:**
- Only goes back ONE migration at a time
- Data loss is possible (e.g., dropping a column deletes data)
- Use with caution in production!

---

## 🎯 Common Workflows

### Workflow 1: Adding a New Feature

```bash
# 1. Modify your model
# Edit backend/app/db/models.py
# Example: Add 'email' field to Broker model

# 2. Create migration
./dev.sh db:migrate "add email to broker"

# 3. Review the generated migration file
# Open backend/alembic/versions/[new_file].py

# 4. Apply the migration
./dev.sh db:upgrade

# 5. Verify
./dev.sh db:current
./dev.sh test db validate

# 6. Commit everything
git add backend/alembic/versions/
git add backend/app/db/models.py
git commit -m "Add email field to broker"
```

### Workflow 2: Pulling Changes from Git

```bash
# 1. Pull latest code
git pull

# 2. Check if there are new migrations
ls backend/alembic/versions/

# 3. Apply new migrations
./dev.sh db:upgrade

# 4. Verify everything works
./dev.sh test db all
./dev.sh server
```

### Workflow 3: Fresh Database Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd LibreFolio

# 2. Install dependencies
./dev.sh install

# 3. Create database from scratch
./dev.sh db:upgrade

# 4. Verify
./dev.sh db:current
./dev.sh test db validate

# 5. Start working
./dev.sh server
```

### Workflow 4: Fixing a Bad Migration

```bash
# 1. You applied a migration that broke things
./dev.sh db:upgrade
# Error: Something went wrong!

# 2. Rollback
./dev.sh db:downgrade

# 3. Fix the migration file manually
# Edit backend/alembic/versions/[problematic_file].py

# 4. Try again
./dev.sh db:upgrade

# 5. If still broken, delete the migration and recreate
rm backend/alembic/versions/[problematic_file].py
./dev.sh db:migrate "fixed version of feature"
./dev.sh db:upgrade
```

---

## 🔍 Understanding Migration Files

Each migration file has:

```python
# Unique revision ID (like a git commit hash)
revision = 'abc123def456'

# Points to previous migration (forms a chain)
down_revision = '37d14b3d7a82'

# Human-readable description
def upgrade() -> None:
    """Apply changes to database."""
    op.create_table('new_table', ...)

def downgrade() -> None:
    """Revert changes."""
    op.drop_table('new_table')
```

**Migration chain example:**
```
Initial schema (37d14b3d7a82)
    ↓
Add user table (abc123def456)
    ↓
Add email column (def789ghi012)
    ↓
[current]
```

---

## 📊 The `alembic_version` Table

Your database has a special table that Alembic manages:

```sql
sqlite> SELECT * FROM alembic_version;
version_num
-----------
abc123def456
```

**This table:**
- Has exactly ONE row
- Stores the current revision ID
- Is automatically updated by Alembic
- **Never edit it manually!**

---

## ⚠️ Common Mistakes & Solutions

### Mistake 1: Forgetting to run `db:upgrade`

```bash
# ❌ Wrong
./dev.sh db:migrate "add feature"
./dev.sh server  # Server crashes - database doesn't have new column!

# ✅ Correct
./dev.sh db:migrate "add feature"
./dev.sh db:upgrade              # Apply the migration!
./dev.sh server                  # Now it works
```

### Mistake 2: Editing models without migration

```bash
# You change models.py but forget to create migration
./dev.sh server  # Code expects new column, database doesn't have it = ERROR

# Fix:
./dev.sh db:migrate "catch up with model changes"
./dev.sh db:upgrade
```

### Mistake 3: Manual database changes

```bash
# ❌ Never do this
sqlite3 backend/data/sqlite/app.db
> ALTER TABLE assets ADD COLUMN foo TEXT;

# Alembic doesn't know about this change!
# Next migration might conflict or get confused

# ✅ Always use migrations
./dev.sh db:migrate "add foo column"
./dev.sh db:upgrade
```

---

## 🔗 How Alembic Knows the Order of Migrations

**Question:** If I create migrations at different times, how does Alembic know which comes first?

**Answer:** Alembic uses a **linked chain** (like a linked list in programming)!

### Migration Chain Example

Each migration file has two key fields:

```python
# File: abc123_add_email.py
revision = 'abc123'          # This migration's ID
down_revision = 'xyz789'     # Points to PREVIOUS migration
```

**Example chain:**

```python
# Migration 1 (first ever)
revision = 'xyz789'
down_revision = None         # ← No previous (it's first!)

# Migration 2
revision = 'abc123' 
down_revision = 'xyz789'     # ← Points to migration 1

# Migration 3
revision = 'def456'
down_revision = 'abc123'     # ← Points to migration 2
```

**Visual chain:**
```
None → xyz789 → abc123 → def456 → (head)
       [1]      [2]      [3]      current
```

### Important Notes

1. **Timestamp is just for humans!**
   ```
   abc123_add_email_20251029_153000.py
          ↑              ↑
       description    timestamp (ignored by Alembic)
   ```
   
2. **Alembic only uses `down_revision`** to determine order
   
3. **The chain never lies** - Alembic follows it strictly

4. **Breaking the chain = broken migrations**
   - Never manually edit `revision` or `down_revision`
   - Always use `db:migrate` to create new migrations

---

## 📦 Should You Commit Migrations to Git?

**Answer:** It depends on your development phase!

### ❌ During Initial Development (Now)

**NO, don't commit yet!** Here's why:

```bash
# Typical scenario during unstable development:
./dev.sh db:migrate "add users"        # Migration 001
# Oops, wrong model!
./dev.sh db:migrate "fix users"        # Migration 002  
# Still wrong!
./dev.sh db:migrate "really fix users" # Migration 003

# Result: 3 migrations for ONE feature! 😱
```

**Better approach:**

```bash
# During unstable development
rm backend/alembic/versions/*.py     # Delete all migrations
rm backend/data/sqlite/app.db        # Delete database
./dev.sh db:migrate "initial schema" # One clean migration
./dev.sh db:upgrade                  # Apply it

# Now you have ONE clean migration! ✨
```

**Temporary .gitignore:**

Add this to your `.gitignore` while developing:
```gitignore
# Temporary: remove when schema is stable
backend/alembic/versions/*.py
```

### ✅ When Schema is Stable

**YES, commit migrations!** They are essential for:

1. **Team collaboration** - Other developers need them
2. **Production deployment** - Server needs to upgrade
3. **History tracking** - See how schema evolved
4. **Rollback capability** - Can go back if needed

**When is schema "stable"?**
- ✅ Core tables defined and tested
- ✅ No major structure changes expected soon
- ✅ Ready for other developers to use
- ✅ Ready to deploy to staging/production

**Remove from .gitignore and commit:**

```bash
# Remove temporary exclusion from .gitignore
# Then commit
git add backend/alembic/versions/
git add backend/app/db/models.py
git commit -m "Add stable database schema with migrations"
```

### 🎯 Development Workflow Strategy

**Phase 1: Unstable (Now)**
```bash
# Ignore migrations in git
echo "backend/alembic/versions/*.py" >> .gitignore

# Iterate freely
# Change models → db:migrate → test → not happy?
# Delete everything and start over!
rm backend/alembic/versions/*.py
rm backend/data/sqlite/app.db
./dev.sh db:migrate "schema v2"
```

**Phase 2: Stabilizing**
```bash
# Schema mostly good, but still tweaking
# Keep migrations in git, but squash before each commit
git reset --soft HEAD~1  # Undo last commit
rm backend/alembic/versions/*.py
./dev.sh db:migrate "stable schema v1"
git add -A
git commit -m "Stable schema v1"
```

**Phase 3: Stable (Production Ready)**
```bash
# Remove from .gitignore
sed -i '' '/backend\/alembic\/versions/d' .gitignore

# Now commit every migration
./dev.sh db:migrate "add user email"
./dev.sh db:upgrade
git add backend/alembic/versions/
git commit -m "Add email field to users"
```

---

## 🎓 Quick Reference

| Command | What it does | When to use |
|---------|--------------|-------------|
| `db:current` | Show current migration | Check status |
| `db:migrate "msg"` | Create new migration | After changing models |
| `db:upgrade` | Apply pending migrations | After `db:migrate` or `git pull` |
| `db:downgrade` | Undo last migration | Fix mistakes |

**Golden Rule (Stable Schema):** 
> Every change to `models.py` needs a migration!
> 1. Change model → 2. `db:migrate` → 3. `db:upgrade` → 4. Commit

**Development Rule (Unstable Schema):**
> Keep iterating until happy, THEN create final migration!
> 1. Experiment freely → 2. When done: delete all migrations
> 3. Create ONE clean migration → 4. Commit when stable

---

## 🚀 Pro Tips

1. **Always check migrations before applying:**
   ```bash
   ./dev.sh db:migrate "add feature"
   # Look at the generated file in backend/alembic/versions/
   # Make sure it does what you expect!
   ./dev.sh db:upgrade
   ```

2. **Use descriptive migration messages:**
   ```bash
   # ❌ Bad
   ./dev.sh db:migrate "update"
   
   # ✅ Good
   ./dev.sh db:migrate "add email and phone to broker table"
   ```

3. **Test migrations before committing:**
   ```bash
   ./dev.sh db:migrate "new feature"
   ./dev.sh db:upgrade
   ./dev.sh test db all  # Make sure everything still works!
   ```

4. **Fresh start when confused:**
   ```bash
   rm backend/data/sqlite/app.db
   ./dev.sh db:upgrade
   ./dev.sh test db populate
   ```

---

## ❓ Frequently Asked Questions

### Q: I made a mistake in a migration, what do I do?

**A:** If not committed yet:

```bash
rm backend/alembic/versions/[mistake_file].py
rm backend/data/sqlite/app.db
./dev.sh db:migrate "corrected version"
./dev.sh db:upgrade
```

If already committed and others are using it:
```bash
# Create a NEW migration to fix it
./dev.sh db:migrate "fix previous mistake"
./dev.sh db:upgrade
```

**Never** edit old migrations that others have already applied!

---

### Q: My database is corrupted, how do I start fresh?

**A:**
```bash
rm backend/data/sqlite/app.db        # Delete database
./dev.sh db:upgrade                  # Recreate from migrations
./dev.sh test db populate            # Add sample data
```

Or use the reset command:
```bash
./dev.sh test --reset db all
```

---

### Q: I pulled code and got "Can't locate revision xyz"?

**A:** Someone added a new migration. Apply it:
```bash
./dev.sh db:upgrade
```

If that fails, your database might be out of sync:
```bash
./dev.sh db:current                  # Check current version
git log backend/alembic/versions/    # See what changed
# If really broken: start fresh
rm backend/data/sqlite/app.db
./dev.sh db:upgrade
```

---

### Q: Can I rename a migration file?

**A:** **Better not!** The filename doesn't matter to Alembic, but:
- Don't rename - it confuses other developers
- Don't change `revision` or `down_revision` fields
- If you must, delete and recreate the migration

---

### Q: Can I skip a migration?

**A:** **Don't!** Alembic migrations form a chain. Skipping breaks everything.

If you really need to skip one:
1. Edit the migration file to make it do nothing (empty `upgrade()` and `downgrade()`)
2. Or: start fresh with a clean database

---

## 📚 Further Reading

- [Alembic Official Docs](https://alembic.sqlalchemy.org/)
- [SQLModel Docs](https://sqlmodel.tiangolo.com/)

---

**Remember:** Migrations are like git commits for your database. Use them wisely! 🎯

---

**Need help?**? Join our community or check the [Main README](../README.md)!
