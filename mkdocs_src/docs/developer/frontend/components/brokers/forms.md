# 📝 Broker Forms

Form and input components for broker creation and editing.

---

## BrokerForm

The create/edit form for a broker. Used inside `BrokerModal`.

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
    <img class="gallery-img" data-category="brokers" data-name="edit-modal" alt="Broker Edit Form" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### Fields

| Field | Component | Required | Description |
|-------|-----------|----------|-------------|
| **Name** | Text input | ✅ | Broker display name |
| **Description** | Textarea | ❌ | Optional description |
| **Base Currency** | [CurrencySearchSelect](../select.md#currencysearchselect) | ✅ | Default currency for cash tracking |
| **Portal URL** | Text input | ❌ | Broker website (used for favicon fallback) |
| **Icon** | [ImagePickerWrapper](../file-upload.md) | ❌ | Custom broker icon |
| **Default Plugin** | [ImportPluginSelect](../select.md#importpluginselect) | ❌ | Default BRIM parser for this broker |
| **Allow Overdraft** | Toggle | ❌ | Allow negative cash balance |

### Validation

- **Name**: Required, minimum 1 character
- **Currency**: Required, must be a valid ISO 4217 code

---

## BrokerIcon

A smart icon component with a **4-step fallback chain**:

```mermaid
graph LR
    A["icon_url<br/><small>Custom uploaded</small>"] -->|not set| B["portal_url favicon<br/><small>Google Favicon API</small>"]
    B -->|not found| C["Plugin icon<br/><small>From BRIM plugin API</small>"]
    C -->|not found| D["Briefcase ✉️<br/><small>Default Lucide icon</small>"]

    style A fill:#e8f5e9,stroke:#2e7d32
    style B fill:#e3f2fd,stroke:#1565c0
    style C fill:#fff3e0,stroke:#e65100
    style D fill:#f3e5f5,stroke:#7b1fa2
```

### Sizes

| Size | Dimensions | Used in |
|------|-----------|---------|
| `sm` | 24×24 px | Inline references, select options |
| `md` | 32×32 px | BrokerCard, list items |
| `lg` | 48×48 px | Broker detail page header |

### Key Props

| Prop | Type | Description |
|------|------|-------------|
| `iconUrl` | `string \| null` | Custom icon URL (step 1) |
| `portalUrl` | `string \| null` | Broker website for favicon (step 2) |
| `pluginCode` | `string \| null` | BRIM plugin code for icon (step 3) |
| `size` | `'sm' \| 'md' \| 'lg'` | Icon size |
| `altText` | `string` | Accessible alt text |

**Used by**: [BrokerCard](cards.md), [BrokerSearchSelect](../select.md#brokersearchselect), broker detail page.

