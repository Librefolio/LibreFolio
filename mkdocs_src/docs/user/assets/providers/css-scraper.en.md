# 🔍 CSS Scraper Provider

The CSS Scraper provider lets you extract price data from any web page using CSS selectors. This is particularly useful for instruments not covered by other providers, such as Italian government bonds (BTP) on Borsa Italiana.

## 📊 Capabilities

- ✅ **Current Price**: Scrapes the price from a web page
- ❌ **History**: Not supported (⚠️ warning, not an error)
- ❌ **Search**: Not supported

## 🔧 Configuration

- **Identifier**: The full URL of the page to scrape
- **Identifier Type**: `OTHER`
- **Parameters**:

| Parameter | Required | Description | Example |
|-----------|:---:|---|---|
| `current_css_selector` | ✅ | CSS selector for the price element | `.summary-value strong` |
| `currency` | ✅ | ISO 4217 currency code | `EUR` |
| `decimal_format` | ❌ | `us` (1,234.56) or `eu` (1.234,56) | `eu` |
| `timeout` | ❌ | HTTP timeout in seconds (default: 30) | `30` |
| `user_agent` | ❌ | Custom User-Agent header | `LibreFolio/1.0` |

## 🔎 How to Find the CSS Selector

### Step-by-step (Chrome)

1. Open the page with the price in Chrome
2. **Right-click** on the price value
3. Select **Inspect** (or press `F12`)
4. In the DevTools Elements panel, the price element will be highlighted
5. **Right-click** the highlighted element in DevTools
6. Select **Copy** → **Copy selector**
7. Paste it into the `current_css_selector` field

### Step-by-step (Firefox)

1. Open the page with the price in Firefox
2. **Right-click** on the price value
3. Select **Inspect Element** (or press `F12`)
4. In the Inspector, **right-click** the highlighted element
5. Select **Copy** → **CSS Selector**
6. Paste it into the `current_css_selector` field

### 💡 Example: Borsa Italiana BTP

For a BTP on Borsa Italiana (e.g., `IT0005634800`):

**URL** (English version):
```
https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en
```

**CSS Selector**:
```
.summary-value strong
```

**Configuration**:
- Identifier: `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
- `current_css_selector`: `.summary-value strong`
- `currency`: `EUR`
- `decimal_format`: `us` (English page uses US format: 100.39)

For the Italian version, use `decimal_format`: `eu` (Italian page uses EU format: 100,39).

## 🔢 Decimal Format

| Format | Example | When to use |
|--------|---------|-------------|
| `us` | 1,234.56 | English/US pages (period as decimal separator) |
| `eu` | 1.234,56 | Italian/German/French pages (comma as decimal separator) |

## 🛠️ Troubleshooting

### "Selector not found"
The CSS selector doesn't match any element on the page. The page structure may have changed — re-inspect and copy a new selector.

### "Connection timeout"
The page took too long to respond. Try increasing the `timeout` parameter or check if the URL is correct.

### "Parse error"
The price text couldn't be parsed as a number. Check the `decimal_format` setting — if the page shows `100,39`, use `eu`; if `100.39`, use `us`.

### Price shows 0 or wrong value
The selector may be matching a different element. Try a more specific selector. Use DevTools to verify exactly which element your selector matches.

