# LibreFolio - Quick E2E Test Commands

**Quick Reference**: Copy-paste commands for rapid testing  
**Full Guide**: See `docs/E2E_TESTING_GUIDE.md` for detailed explanations

---

## 🚀 Setup (Run Once)

```bash
# Start server
./dev.sh server

# In another terminal, set base URL
export BASE_URL="http://localhost:8000/api/v1"

# Verify server
curl -s "$BASE_URL/health" | jq
```

---

## 📝 Quick Test Flow (5 minutes)

### 1. Create Asset with Metadata

```bash
curl -X POST "$BASE_URL/assets/bulk" -H "Content-Type: application/json" -d '{"assets":[{"display_name":"Apple Inc.","identifier":"AAPL","identifier_type":"TICKER","currency":"USD","asset_type":"STOCK","valuation_model":"MARKET_PRICE","classification_params":{"investment_type":"stock","sector":"Technology","geographic_area":{"USA":"0.60","CHN":"0.25","EUR":"0.15"}}}]}' | jq
```

**Save asset_id from response** → `export ASSET_ID_1=1`

### 2. Create Asset + Assign yfinance Provider (Auto-Metadata)

```bash
# Create asset
curl -X POST "$BASE_URL/assets/bulk" -H "Content-Type: application/json" -d '{"assets":[{"display_name":"Microsoft Corporation","identifier":"MSFT","identifier_type":"TICKER","currency":"USD","asset_type":"STOCK","valuation_model":"MARKET_PRICE"}]}' | jq

# Save asset_id → export ASSET_ID_2=2

# Assign provider (will auto-populate metadata)
curl -X POST "$BASE_URL/assets/${ASSET_ID_2}/provider" -H "Content-Type: application/json" -d '{"provider_code":"yfinance"}' | jq
```

### 3. Verify Metadata Auto-Populated

```bash
curl -X POST "$BASE_URL/assets" -H "Content-Type: application/json" -d "{\"asset_ids\":[$ASSET_ID_2]}" | jq '.[].classification_params'
```

### 4. PATCH Metadata (Update Geographic Area)

```bash
curl -X PATCH "$BASE_URL/assets/metadata" -H "Content-Type: application/json" -d "{\"assets\":[{\"asset_id\":$ASSET_ID_2,\"patch\":{\"geographic_area\":{\"USA\":\"0.50\",\"EUR\":\"0.30\",\"ASIA\":\"0.20\"}}}]}" | jq
```

### 5. Verify Changes Persisted

```bash
curl -X POST "$BASE_URL/assets" -H "Content-Type: application/json" -d "{\"asset_ids\":[$ASSET_ID_2]}" | jq '.[].classification_params.geographic_area'
```

### 6. List All Assets

```bash
curl -X GET "$BASE_URL/assets/list" | jq
```

### 7. Refresh Metadata from Provider

```bash
curl -X POST "$BASE_URL/assets/${ASSET_ID_2}/metadata/refresh" | jq
```

### 8. Fetch Prices from yfinance

```bash
curl -X POST "$BASE_URL/assets/${ASSET_ID_2}/prices-refresh?start_date=2025-11-01&end_date=2025-11-22&force=false" | jq
```

### 9. Query Prices (with Backward-Fill)

```bash
curl -X GET "$BASE_URL/assets/${ASSET_ID_2}/prices?start_date=2025-11-15&end_date=2025-11-22" | jq
```

### 10. Delete Assets (Cleanup)

```bash
curl -X DELETE "$BASE_URL/assets/bulk" -H "Content-Type: application/json" -d "{\"asset_ids\":[$ASSET_ID_1,$ASSET_ID_2]}" | jq
```

---

## ✅ Quick Verification Checklist

After running above commands, check:

- [ ] Asset 1 created with manual metadata
- [ ] Asset 2 created and yfinance provider assigned
- [ ] Asset 2 metadata auto-populated (sector, description, geographic_area)
- [ ] PATCH updated only geographic_area (other fields unchanged)
- [ ] Changes persisted in database
- [ ] List returned both assets
- [ ] Metadata refresh from provider works
- [ ] Prices fetched from Yahoo Finance
- [ ] Backward-fill works for weekends
- [ ] Assets deleted successfully

---

## 🧪 Additional Test Scenarios

### Test Invalid Geographic Area (should fail)

```bash
curl -X PATCH "$BASE_URL/assets/metadata" -H "Content-Type: application/json" -d '{"assets":[{"asset_id":1,"patch":{"geographic_area":{"USA":"0.50","EUR":"0.60"}}}]}' | jq
```

**Expected**: Error message "sum must be 1.0"

### Test Lowercase Currency (should auto-uppercase)

```bash
curl -X POST "$BASE_URL/assets/bulk" -H "Content-Type: application/json" -d '{"assets":[{"display_name":"Test","identifier":"TEST","identifier_type":"TICKER","currency":"eur","asset_type":"STOCK","valuation_model":"MARKET_PRICE"}]}' | jq
# Verify currency is "EUR" not "eur"
```

### Test Duplicate Identifier (should fail)

```bash
curl -X POST "$BASE_URL/assets/bulk" -H "Content-Type: application/json" -d '{"assets":[{"display_name":"Dup1","identifier":"DUP","identifier_type":"TICKER","currency":"USD","asset_type":"STOCK","valuation_model":"MARKET_PRICE"},{"display_name":"Dup2","identifier":"DUP","identifier_type":"TICKER","currency":"USD","asset_type":"STOCK","valuation_model":"MARKET_PRICE"}]}' | jq
```

**Expected**: First succeeds, second fails with "already exists"

---

## 🗑️ Quick Cleanup

```bash
# Delete all assets
ASSET_IDS=$(curl -s "$BASE_URL/assets/list" | jq '[.[].asset_id]')
curl -X DELETE "$BASE_URL/assets/bulk" -H "Content-Type: application/json" -d "{\"asset_ids\":$ASSET_IDS}" | jq

# Verify empty
curl -s "$BASE_URL/assets/list" | jq 'length'  # Should be 0
```

---

## 📚 Full Documentation

See `docs/E2E_TESTING_GUIDE.md` for:
- Detailed explanations
- Expected outputs
- Troubleshooting
- Complete test scenarios

