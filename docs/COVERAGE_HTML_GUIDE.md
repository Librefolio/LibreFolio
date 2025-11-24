# How to View Coverage Report (Visual Line-by-Line)

**Generated**: November 24, 2025  
**Report Location**: `htmlcov/index.html`

---

## 🎨 Visual Coverage Report

### **What You Get**

The HTML coverage report shows **exactly which lines were executed** during tests:

- 🟢 **Green lines** = Covered (executed during tests)
- 🔴 **Red lines** = Not covered (never executed)
- 🟡 **Yellow lines** = Partially covered (branch not taken)
- ⚪ **White lines** = Comments/blank lines

---

## 🚀 How to Open

### **Method 1: Command Line**

```bash
open htmlcov/index.html
```

### **Method 2: Browser**

Navigate to:
```
file:///home/alfy/Documenti/02_myRepo/LibreFolio_prj/LibreFolio/htmlcov/index.html
```

### **Method 3: From IDE**

Right-click `htmlcov/index.html` → Open in Browser

---

## 📊 What You'll See

### **1. Index Page** (`index.html`)

**Shows**:
- Overall coverage percentage
- List of all Python files in `backend/app/`
- Coverage % for each file
- Number of statements
- Number of missing lines

**Example**:
```
File                                    Stmts   Miss  Cover   Missing
------------------------------------------------------------------
backend/app/utils/decimal_utils.py        28      2    93%   56, 77
backend/app/utils/financial_math.py      111      6    95%   71, 114, 157
backend/app/schemas/assets.py            256     18    93%   370-373, 379-381
```

**Click any file** to see line-by-line coverage!

---

### **2. File View** (Click a file)

**Shows**:
- Syntax-highlighted source code
- Line numbers
- Coverage status (green/red/yellow)
- Run/miss counters per line

**Example Screenshot** (what you'll see):

```python
  1  from decimal import Decimal                          # ✅ GREEN (covered)
  2                                                        # (blank)
  3  def truncate_decimal(value, precision):              # ✅ GREEN
  4      """Truncate decimal to precision."""            # ✅ GREEN
  5      if value is None:                                # ✅ GREEN
  6          return None                                  # ✅ GREEN
  7      quantizer = Decimal(10) ** -precision            # ✅ GREEN
  8      return Decimal(value).quantize(quantizer)        # ✅ GREEN
  9                                                        # (blank)
 10  def untested_function():                             # ❌ RED (not covered!)
 11      return "this was never called"                   # ❌ RED
```

**Features**:
- Hover over line numbers to see how many times executed
- Click line numbers to anchor to that line
- Use keyboard shortcuts (see help icon)

---

### **3. Navigation**

**Top Menu**:
- **index** - Back to file list
- **class** - List all classes
- **function** - List all functions

**Search**:
- Type to filter files/functions
- Keyboard shortcuts available (press `?` for help)

**Sort**:
- Click column headers to sort
- Default: sort by filename

---

## 🎯 How to Use for Development

### **Workflow 1: Find What Needs Testing**

1. Run tests with coverage:
   ```bash
   ./test_runner.py --coverage utils all
   ```

2. Open report:
   ```bash
   open htmlcov/index.html
   ```

3. **Look for red lines** - these need tests!

4. **Find files with low coverage** (<80%)

5. Write tests for red lines

6. Re-run coverage to verify

---

### **Workflow 2: Verify Your Test Covers What You Expect**

**Scenario**: You wrote a test for `calculate_interest()` function

1. Run coverage:
   ```bash
   ./test_runner.py --coverage utils compound-interest
   ```

2. Open `htmlcov/index.html`

3. Navigate to `backend/app/utils/financial_math.py`

4. **Scroll to `calculate_interest()` function**

5. **Check all lines are green** ✅

6. If any lines are red ❌:
   - Those branches/conditions weren't tested
   - Add more test cases

---

### **Workflow 3: Incremental Coverage**

**Goal**: Increase coverage from 28% to 85%

1. **Baseline** (now):
   ```bash
   ./test_runner.py --coverage utils all
   # Coverage: 28%
   ```

2. **Convert service tests** to pytest:
   ```bash
   # After conversion
   ./test_runner.py --coverage services all
   # Coverage: ~58% (estimated)
   ```

3. **Convert API tests**:
   ```bash
   ./test_runner.py --coverage api all
   # Coverage: ~73% (estimated)
   ```

4. **Run everything**:
   ```bash
   ./test_runner.py --coverage all
   # Coverage: ~85% (target)
   ```

5. **Check report** - which files still have red lines?

6. **Write tests for remaining red lines**

---

## 📈 Coverage Goals

### **Current State** (after utils tests):
```
Overall: 28%
  ✅ Utils:     93-99% (excellent!)
  ❌ Services:  0%     (needs conversion)
  ❌ API:       0%     (needs conversion)
  ❌ DB:        38%    (partial)
```

### **Target State** (after all conversions):
```
Overall: 85-90%
  ✅ Utils:     95%+
  ✅ Services:  85%+
  ✅ API:       90%+
  ✅ DB:        80%+
  ✅ Schemas:   95%+
```

### **Acceptable Gaps**:
- Unreachable error handlers: OK
- Defensive code paths: OK
- Migration scripts: OK (not production code)
- CLI entry points: OK (tested manually)

---

## 🔍 Advanced Features

### **Branch Coverage**

Shows if **all branches** of conditionals were tested:

```python
def calculate(x):
    if x > 0:        # Branch 1: True path
        return x     # ✅ Covered
    else:            # Branch 2: False path
        return -x    # ❌ Not covered!
```

**Report shows**:
```
Line 2: Branch 0 taken, Branch 1 not taken
```

### **Multiple Test Runs**

Coverage **accumulates** with `--cov-append`:

```bash
# Run utils tests
./test_runner.py --coverage utils all
# Coverage: 28%

# Run services tests (appends)
./test_runner.py --coverage services all
# Coverage: 58% (cumulative!)

# Run API tests (appends more)
./test_runner.py --coverage api all
# Coverage: 73% (cumulative!)
```

**To start fresh**:
```bash
# Delete old coverage data
rm .coverage

# Run tests
./test_runner.py --coverage all
```

### **Coverage Data Files**

- `.coverage` - Binary database (coverage.py format)
- `htmlcov/` - HTML report (human-readable)
- `coverage.json` - JSON export (machine-readable)

---

## 💡 Tips & Tricks

### **Tip 1: Focus on Low-Hanging Fruit**

**Look for**:
- Files with 50-80% coverage (easy to improve)
- Simple utility functions (quick to test)
- Schema validators (just need test cases)

**Avoid**:
- Files with 0% coverage (need full test conversion)
- Complex integration tests (time-consuming)

### **Tip 2: Use File Search**

In HTML report:
1. Press `Ctrl+F` or `Cmd+F`
2. Type function/class name
3. Jump directly to it

### **Tip 3: Print Coverage to Terminal**

```bash
# Show missing lines in terminal
./test_runner.py --coverage utils all

# Terminal output includes:
backend/app/utils/decimal_utils.py      93%   56, 77
                                              ^^^^^^
                                              Missing lines!
```

### **Tip 4: Compare Before/After**

```bash
# Before adding tests
./test_runner.py --coverage services fx
# Services coverage: 45%

# Add more test cases
# ... edit test_fx_conversion.py ...

# After
./test_runner.py --coverage services fx
# Services coverage: 78% ✅ (+33%!)
```

---

## 📚 Interactive Example

### **Let's Find What's Not Tested**

**Step 1**: Run coverage
```bash
./test_runner.py --coverage utils all
open htmlcov/index.html
```

**Step 2**: Click `backend/app/utils/datetime_utils.py`

**Step 3**: You'll see something like:
```python
  1  from datetime import datetime                        # ✅ GREEN
  2  from zoneinfo import ZoneInfo                        # ✅ GREEN
  3                                                        
  4  def now_utc():                                       # ✅ GREEN
  5      return datetime.now(ZoneInfo('UTC'))            # ✅ GREEN
  6                                                        
  7  def parse_datetime(s):                               # ❌ RED
  8      return datetime.fromisoformat(s)                # ❌ RED
```

**Step 4**: You now know:
- ✅ `now_utc()` is tested
- ❌ `parse_datetime()` is NOT tested

**Step 5**: Add test for `parse_datetime()`

**Step 6**: Re-run coverage → line 7-8 turn green ✅

---

## 🎉 Summary

**Coverage HTML Report Gives You**:

1. ✅ **Visual feedback** - see exactly what's tested (green/red)
2. ✅ **File-by-file breakdown** - prioritize which files need work
3. ✅ **Line numbers** - know exactly which lines to test
4. ✅ **Branch coverage** - ensure all code paths tested
5. ✅ **Interactive** - click around, search, sort
6. ✅ **Beautiful** - syntax highlighting, professional look

**Next Steps**:

1. Run: `./test_runner.py --coverage utils all`
2. Open: `open htmlcov/index.html`
3. Explore: Click files, see green/red lines
4. Improve: Write tests for red lines
5. Repeat: Until coverage reaches 85%+

**That's it!** The visual report makes it super easy to see what needs testing. 🎨✨

---

**Last Updated**: November 24, 2025  
**Your Current Coverage**: 28% (utils only)  
**Target Coverage**: 85-90% (after test conversions)

