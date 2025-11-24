# LibreFolio - Geographic Area Country Codes Reference

**Last Updated**: November 24, 2025  
**Purpose**: Quick reference for country codes used in `geographic_area` field

---

## 📋 Overview

LibreFolio uses **ISO 3166-1 alpha-3** codes (3-letter uppercase) for country identification in asset classification metadata.

**Key Points**:
- ✅ Always use ISO 3166-1 alpha-3 codes (USA, CHN, FRA, etc.)
- ✅ System normalizes ISO-2 (US) and country names (United States) to ISO-3
- ❌ Avoid ambiguous codes like "EUR" (Europe is not a country)
- ❌ Avoid region names like "ASIA" (not a specific country)

---

## 🌍 Common ISO 3166-1 alpha-3 Codes

### North America
| Code | Country |
|------|---------|
| USA | United States of America |
| CAN | Canada |
| MEX | Mexico |

### South America
| Code | Country |
|------|---------|
| BRA | Brazil |
| ARG | Argentina |
| CHL | Chile |
| COL | Colombia |
| PER | Peru |

### Europe
| Code | Country |
|------|---------|
| DEU | Germany |
| FRA | France |
| GBR | United Kingdom |
| ITA | Italy |
| ESP | Spain |
| NLD | Netherlands |
| BEL | Belgium |
| CHE | Switzerland |
| AUT | Austria |
| SWE | Sweden |
| NOR | Norway |
| DNK | Denmark |
| FIN | Finland |
| POL | Poland |
| PRT | Portugal |
| IRL | Ireland |
| CZE | Czech Republic |
| GRC | Greece |
| HUN | Hungary |
| ROU | Romania |
| SVK | Slovakia |

### Asia
| Code | Country |
|------|---------|
| CHN | China |
| JPN | Japan |
| IND | India |
| KOR | South Korea |
| IDN | Indonesia |
| THA | Thailand |
| MYS | Malaysia |
| SGP | Singapore |
| PHL | Philippines |
| VNM | Vietnam |
| PAK | Pakistan |
| BGD | Bangladesh |
| TWN | Taiwan |
| HKG | Hong Kong |

### Middle East
| Code | Country |
|------|---------|
| SAU | Saudi Arabia |
| ARE | United Arab Emirates |
| ISR | Israel |
| TUR | Turkey |
| IRN | Iran |
| IRQ | Iraq |
| QAT | Qatar |
| KWT | Kuwait |

### Africa
| Code | Country |
|------|---------|
| ZAF | South Africa |
| EGY | Egypt |
| NGA | Nigeria |
| KEN | Kenya |
| MAR | Morocco |
| ETH | Ethiopia |
| GHA | Ghana |

### Oceania
| Code | Country |
|------|---------|
| AUS | Australia |
| NZL | New Zealand |

---

## 🔍 Normalization Examples

### ✅ Valid Inputs (All normalize correctly)

| Your Input | Normalized To | Country |
|------------|---------------|---------|
| `"USA"` | `USA` | United States |
| `"US"` | `USA` | United States (ISO-2 → ISO-3) |
| `"United States"` | `USA` | United States (name → ISO-3) |
| `"CHN"` | `CHN` | China |
| `"CN"` | `CHN` | China (ISO-2 → ISO-3) |
| `"China"` | `CHN` | China (name → ISO-3) |
| `"cina"` | `CHN` | China (Italian name) |
| `"FRA"` | `FRA` | France |
| `"FR"` | `FRA` | France (ISO-2 → ISO-3) |
| `"France"` | `FRA` | France (name → ISO-3) |

### ❌ Ambiguous Inputs (Avoid these!)

| Your Input | Problem | What Happens |
|------------|---------|--------------|
| `"eur"` | Not a country | Fuzzy matches to FRA, CZE, or other EU countries (unpredictable!) |
| `"ASIA"` | Region, not country | May match random country or fail |
| `"EU"` | Region code | May match random country or fail |
| `"EMEA"` | Region acronym | May match random country or fail |
| `"Europe"` | Continent | May match random country or fail |

**Why ambiguous?** The system uses `pycountry` fuzzy matching - it tries to find the "closest" country name, but for regions/continents, the result is unpredictable.

---

## 💡 Best Practices

### ✅ DO

1. **Use ISO 3166-1 alpha-3 codes** (3-letter uppercase)
   ```json
   {
     "geographic_area": {
       "USA": "0.60",
       "CHN": "0.25",
       "FRA": "0.15"
     }
   }
   ```

2. **Sum must equal 1.0** (±0.000001 tolerance)
   - ✅ `0.60 + 0.25 + 0.15 = 1.00`
   - ❌ `0.60 + 0.25 + 0.10 = 0.95` (rejected!)

3. **Use 4 decimals max** (automatically quantized)
   - Input: `0.123456`
   - Stored: `0.1235` (rounded)

4. **Check codes before using**
   - Use this reference
   - Or check [ISO 3166-1 Wikipedia](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3)

### ❌ DON'T

1. **Don't use region names**
   - ❌ "EUR", "ASIA", "EMEA", "LatAm"
   - ✅ Use specific countries instead

2. **Don't use ambiguous codes**
   - ❌ "eur" (could be any EU country)
   - ✅ "FRA" (clearly France)

3. **Don't use country names in API** (unless you know they normalize correctly)
   - ⚠️ "United States" works but "US" is clearer
   - ✅ Use ISO-3 codes for predictability

4. **Don't forget to validate sum**
   - System will reject if sum != 1.0 (outside tolerance)

---

## 🔧 How to Find Country Codes

### Method 1: Use Python (Local)

```python
import pycountry

# Search by name
country = pycountry.countries.search_fuzzy("Italy")[0]
print(country.alpha_3)  # Output: ITA

# List all countries
for country in pycountry.countries:
    print(f"{country.alpha_3} - {country.name}")
```

### Method 2: Online Resources

- [ISO 3166-1 Wikipedia](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-3) - Complete list
- [pycountry Documentation](https://pypi.org/project/pycountry/) - Python library used by LibreFolio

### Method 3: API Response

When yfinance auto-populates metadata, it uses correct ISO-3 codes:

```bash
# Assign yfinance provider
curl -X POST "$BASE_URL/assets/1/provider" \
  -H "Content-Type: application/json" \
  -d '{"provider_code": "yfinance"}'

# Check geographic_area in response
# Will show normalized ISO-3 codes
```

---

## 📊 Example: Multi-Country Portfolio

### Apple Inc. (Global Company)

```json
{
  "asset_id": 1,
  "display_name": "Apple Inc.",
  "identifier": "AAPL",
  "classification_params": {
    "investment_type": "stock",
    "sector": "Technology",
    "geographic_area": {
      "USA": "0.4500",  // 45% revenue from Americas
      "CHN": "0.2500",  // 25% from Greater China
      "JPN": "0.1000",  // 10% from Japan
      "GBR": "0.0800",  // 8% from Europe (UK)
      "DEU": "0.0700",  // 7% from Europe (Germany)
      "FRA": "0.0500"   // 5% from Europe (France)
    }
  }
}
```

### Vanguard S&P 500 ETF (US-Focused)

```json
{
  "asset_id": 2,
  "display_name": "Vanguard S&P 500 ETF",
  "identifier": "VOO",
  "classification_params": {
    "investment_type": "etf",
    "sector": "Diversified",
    "geographic_area": {
      "USA": "1.0000"  // 100% US equities
    }
  }
}
```

### iShares MSCI Emerging Markets ETF (Diversified EM)

```json
{
  "asset_id": 3,
  "display_name": "iShares MSCI Emerging Markets ETF",
  "identifier": "EEM",
  "classification_params": {
    "investment_type": "etf",
    "sector": "Diversified",
    "geographic_area": {
      "CHN": "0.3200",  // 32% China
      "IND": "0.1800",  // 18% India
      "TWN": "0.1500",  // 15% Taiwan
      "BRA": "0.0700",  // 7% Brazil
      "ZAF": "0.0600",  // 6% South Africa
      "KOR": "0.1200",  // 12% South Korea
      "MEX": "0.0500",  // 5% Mexico
      "THA": "0.0300",  // 3% Thailand
      "IDN": "0.0200"   // 2% Indonesia
    }
  }
}
```

---

## 🚨 Troubleshooting

### Error: "Invalid country code"

**Problem**: Country code not recognized

**Solution**: Check spelling, use ISO 3166-1 alpha-3 code from this reference

```bash
# ❌ Wrong
"geographic_area": {"INVALID": "1.0"}

# ✅ Correct
"geographic_area": {"USA": "1.0"}
```

### Error: "Geographic area sum must equal 1.0"

**Problem**: Weights don't sum to exactly 1.0

**Solution**: Adjust weights to sum to 1.0

```bash
# ❌ Wrong (sum = 0.95)
"geographic_area": {"USA": "0.60", "CHN": "0.25", "FRA": "0.10"}

# ✅ Correct (sum = 1.00)
"geographic_area": {"USA": "0.60", "CHN": "0.25", "FRA": "0.15"}
```

### Unexpected Country in Response

**Problem**: Used ambiguous code like "eur", got unexpected country like CZE

**Solution**: Use specific ISO-3 code

```bash
# ❌ Ambiguous
"geographic_area": {"eur": "0.40"}  # Could become FRA, CZE, DEU, etc.

# ✅ Specific
"geographic_area": {"FRA": "0.40"}  # Always France
```

---

## 📚 Related Documentation

- **E2E Testing Guide**: `docs/E2E_TESTING_GUIDE.md` - Full testing walkthrough
- **API Examples**: `docs/api-examples/asset-management.md` - API usage examples
- **Geo Normalization**: `backend/app/utils/geo_normalization.py` - Source code

---

**Last Updated**: November 24, 2025  
**Maintained By**: LibreFolio Development Team

