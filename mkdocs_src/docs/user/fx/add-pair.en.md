# ➕ Adding a Currency Pair

A pair tells LibreFolio where the rate between two currencies comes from: a central bank provider,
a chain of providers, or rates you enter yourself.

Click **Add Pair** on the [FX page](index.md). The same window opens from the Dashboard, from an
asset page and from the FX step of the PAC allocator.

---

## 🧭 Add a pair step by step

### 💱 Step 1: Pick the two currencies

In **Add New Currency Pair**, choose the **Base Currency** and the **Quote Currency**. Each list
hides the currencies already paired with the other one, so a pair cannot be added twice.

### 🛤️ Step 2: Choose a route

Click **Add conversion route** to see every way the providers can produce this rate:

- 🔗 **Direct conversion (1 step)** — one provider publishes the pair;
- 🔀 **Chain conversion** — steps through other currencies, grouped by number of steps;
- 🚫 **Not usable** — providers that cannot reach this pair.

Filter with the search box (provider, currency or country), then click a route to add it.

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-routes" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="add-pair-routes" data-title="🔗 Direct Routes" alt="Add Pair — Direct Routes">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="add-pair-chain" data-title="🔀 Chain Routes (Multi-hop)" alt="Add Pair — Chain Routes">
</div>

??? tip "🛟 Backup routes — when you add more than one"

    LibreFolio uses route **#1** first and tries **#2** if it fails during a sync, and so on. Drag
    the routes to reorder them; 🗑️ removes one, and ⚠️ shows a note from its provider.

??? note "🔀 Also create intermediate pairs — when you pick a chain route"

    Tick **Also create intermediate pairs** to save each step as a pair of its own. You can then
    sync each step separately and convert into the intermediate currency too: a chain stores only
    the rate of its own pair.

??? note "✏️ No route — manual rates only"

    You can save without a route, then enter the rates yourself in the pair's
    [Data Editor](detail/data-editor.md).

### 💾 Step 3: Save

Click **Save Configuration**; the window closes right away.

- **With a provider**, LibreFolio downloads the pair's **whole history** up to today, whatever
  period the page shows, intermediate pairs included. A message reports the result, in green only
  if everything worked.
- **Without a provider**, a message confirms that the pair was created.

Click the pair's name in the message to open its page.

---

## 🛤️ Direct and chain routes

A **direct route** uses one provider that publishes both currencies, such as the ECB for
EUR 🇪🇺 / USD 🇺🇸. When no central bank publishes the pair, a **chain route** multiplies the rates of
its steps. RON 🇷🇴 / USD 🇺🇸, for example, goes RON → EUR → USD, both steps from the ECB, which
publishes EUR/RON and EUR/USD:

$$
r_{\text{RON}\to\text{USD}} = r_{\text{RON}\to\text{EUR}} \times r_{\text{EUR}\to\text{USD}}
$$

- A chain has a rate only on the days when **every step** has one.
- If one step fails during a sync, the whole chain fails: shorter chains are more reliable.
- A chain rate can differ slightly from a direct market quote.

---

## 🔗 Related

- 🔄 **[Synchronization](sync.md)** — Download rates again later
- 🔌 **[Provider Config](detail/provider.md)** — Change a pair's routes after creating it
- 🧑‍💻 For developers: **[FX Configuration & Routing](../../developer/backend/fx/configuration.md)** and **[FX Chain Algorithm](../../developer/frontend/fx-chain-algorithm.md)**
