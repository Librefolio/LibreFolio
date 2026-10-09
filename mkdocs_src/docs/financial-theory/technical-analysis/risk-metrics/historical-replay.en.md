# ⏮️ Historical Replay

Historical replay applies the movements of a real past episode to the portfolio as it is composed today, asking what that same episode would do now.

It is the question *what would 2008 do to me?* answered arithmetically rather than by recollection — and the value of the answer depends entirely on understanding whose portfolio is being put through that episode.

---

## 🔢 How the Replay Is Computed {: #how-the-replay-is-computed }

You choose an episode — a date range — and the analysis takes the actual returns of each holding over that range. Each asset is given one unit of wealth at the start and compounds on its own:

$$
W_i(t) = W_i(t-1) \cdot \left(1 + r_i(t)\right), \qquad W_i(0) = 1
$$

Portfolio wealth at each step is the weighted sum of those asset wealth indices, plus the cash share:

$$
W_p(t) = c + \sum_i w_i \, W_i(t)
$$

and the portfolio return for the period is the change in that wealth:

$$
r_p(t) = \frac{W_p(t)}{W_p(t-1)} - 1
$$

The cash share $c$ defaults to whatever the asset weights leave over, $c = 1 - \sum_i w_i$, and the weights plus cash are required to sum to $1$. All series must run on one common calendar; returns below $-100\%$ and negative weights are refused.

---

## 🧭 Nothing Is Rebalanced {: #nothing-is-rebalanced }

The weights $w_i$ multiply asset wealth indices that grow apart. Only the **starting** weights are imposed: from the second period onward, the effective composition is whatever compounding has made it.

That is deliberate, and it is the meaning of *buy and hold*. Over a crash, the assets that fall hardest shrink as a share of the portfolio on their own — no rule sells them, and no rule tops them back up. A rebalanced replay would be a different exercise, because rebalancing buys into what has fallen and would report a different outcome for the same episode.

!!! info "Cash earns exactly zero"

    The cash share contributes a constant to portfolio wealth in every period. That is not a neutral choice, it is a specific one with consequences in both directions: through a crash, cash is the part of the portfolio that holds its value, and it will make the replayed loss shallower than the invested holdings alone would suggest. Over a long or inflationary stretch, a zero nominal return is a real loss that the replay does not show, because the replay is stated in nominal terms.

---

## ❓ Whose Portfolio Is Being Replayed {: #whose-portfolio-is-being-replayed }

This is the point on which the result is most often misread.

!!! warning "This is not how your portfolio performed"

    The replay projects **today's** holdings backwards. It answers *how would the portfolio I hold now have fared in that episode?* — not *how did I fare?* The two coincide only if the composition never changed, and they diverge every time a position was bought, sold or resized. Actual past performance is a matter of record and is reported elsewhere; this figure is a hypothetical about a composition that, in many cases, did not exist on those dates.

There is a second, quieter consequence. The portfolio held today is the one that **survived** every decision taken since: positions that were sold, including those sold because they went badly, are not in it. Projecting it backwards carries that selection along with it, so a replay of a bad episode can look more comfortable than the episode actually was — not because the arithmetic is wrong, but because the arithmetic is being applied to a set of holdings chosen with the benefit of everything that happened afterwards.

---

## 🧩 Holdings Without Enough History {: #holdings-without-enough-history }

An episode from 2008 cannot be replayed on a fund launched in 2019: there are no returns to apply. The analysis neither fills the gap with an assumption nor stops: it **leaves the holding out** and replays the others.

Each holding is judged on its own quotes, not on the shared calendar. It takes part only if it is priced at both ends of the window, give or take the seven calendar days of the [staleness threshold](data-quality.md#staleness-threshold): at the start, a quote in the seven days before the window begins — or, for a history that begins inside the window, a first quote no more than seven days after the window begins; at the end, a last quote no more than seven days before the window ends. The test runs before the return series are prepared, and the order matters. The replayed series share one calendar (see [Limitations](#limitations)): a holding that starts late, kept in, would move the start of that calendar and shorten the replay of every other holding to fit its own.

### 🏷️ Why a Holding Is Left Out {: #why-a-holding-is-left-out }

Every holding left out carries exactly one reason:

| Reason | What the holding's quotes show |
|---|---|
| No prices in the period | No quote inside the window, and none in the seven days before it begins. |
| First quoted after the period began | Its history begins inside the window, more than seven days after the start. |
| No recent price when the period began | It was quoted before the window, but not in the seven days before it begins — a gap in an older history, or a sparse rhythm such as a monthly NAV. |
| No recent price at the end of the period | No price in the last seven days of the window. Quotes are read only up to the window's end, so a gap and a delisting look the same there and share this reason. |
| No exchange rate to your currency | No exchange rate from its currency into the currency the analysis is stated in. |
| Left out by you | The reader left it out by hand, where that is possible — see [Proxies](#proxies). |

### ⚖️ What Takes Its Place {: #what-takes-its-place }

What becomes of a holding left out depends on whether the replay has weights.

**On a portfolio** — the Risk tab of the Dashboard or of a broker's page — the holding leaves the replay, but its weight does not. The excluded weight is added to the cash share $c$, which means it is replayed as **earning exactly zero** for the whole episode. That zero belongs to the total, not to the holding: the holding gets no return of its own, and the per-holding returns list only the holdings that were replayed — a zero among them would state a return that nobody measured.

That treatment is worth a moment, because it is not neutral. Leaving a holding out does not make the portfolio smaller; it makes that fraction of the portfolio flat. In an episode where everything fell, a 10% position held flat is an implicit claim that it would have been the best thing you owned. Nobody makes that claim on purpose — the engine applies it on its own — which is why the result names every holding it left out, with its reason and its share of the value.

**On a selection of assets without weights** — the [Correlation tab](../../../user/assets/correlation.md) of the Assets page — there is no cash share to hold anything. The asset is simply omitted: it gets no return at all, not a return of zero, and the figures speak for the assets that were replayed. A selection has no composition to add up, so those per-asset returns are the whole answer.

### 🔎 What the Result Shows {: #what-the-result-shows }

On those three tabs, the replay says what it left out before the figures it reports:

- a warning **above everything else** when more than half of the portfolio's value is left out, stating the share the result still covers: past that point the total speaks for a minority of the portfolio, with the rest held flat beside it;
- as soon as one holding is left out, a box **above the total, where there is one, and the table** lists the holdings left out, **grouped by reason**, each as a badge with its icon and its name — on a portfolio with its share of the value too, under a line stating how much of the value counts as cash at zero return. The [common period](#the-common-period), when there is one, is offered in the same box;
- the table lists only the holdings that were **replayed**, worst first — a click on a column title sorts by that column — each in one row: its **Weight**; its **Return**, its own over the period; its **Contribution**, the weight times that return, so that the contributions add up to the total; its **Impact**, the amount gained or lost; and its **Effect**, a bar in a column you can widen by dragging the edge of its title. The bar shows the contribution on a portfolio and the return on a selection. It grows from a zero line in the middle of the column — losses to the left in red, gains to the right in green — on one scale shared by every row, the largest magnitude reaching the edge. A holding left out has [no return of its own](#what-takes-its-place), so it gets no row, not a row at zero;
- a column with nothing to show is left out, not filled with dashes: a selection of assets has no weights, no contributions and no money, so its table shows just the **Return** and the **Effect**;
- when every holding is left out, no figure: the result says there is **nothing to replay**, and lists the reasons.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="risk" data-name="lab-replay" alt="What if…? on the Correlation tab after Run replay: the box of assets left out, as badges grouped by reason, with the common-period button, above the table of the assets replayed, with Return and Effect" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📆 The Common Period {: #the-common-period }

When the window's edges are what left holdings out — a late start, a gap before the window, no recent price at its end — the analysis proposes the part of the window in which they are priced as well. That part begins the day after the latest first quote, inside the window, of a holding without a price at the start, so that this quote becomes its starting price; it ends at the earliest last quote of a holding without a recent price at the end. Before it is offered, a second reading of the quotes over that shorter window confirms it: every holding it brings back, and every holding the window already covered, must be priced at both of its ends, or nothing is proposed. A holding left out for having no prices in the window, or no exchange rate, is never part of it: no shorter window would bring it back.

On those tabs, the proposal is a button inside the box that lists what was left out: it shows its dates and how many holdings it brings back, and one click replays it — also when nothing at all could be replayed over the original window. When the replay ran over one of the built-in crises — still chosen in the menu, on the crisis's own dates — and the proposal is shorter, it is marked as covering only part of the crisis. That is the trade-off: you get the holdings back, but you replay a shorter stretch than the episode, and whatever the market did outside that stretch is no longer in the answer. Choosing **No preset**, a quick range or a date of your own sets the crisis aside: the next replay is of a period, no longer of the crisis, and carries no such mark.

### 🎭 Proxies {: #proxies }

A proxy lets another asset's return series stand in for a holding without the history. It exists in one place only: the **Risk & Scenarios** tab of an asset's detail page, for that asset alone, where the reader can choose a proxy for it or exclude it instead. A proxied holding is replayed on its proxy's returns instead of being left out, and a proxy with no usable returns over the window is refused as an invalid choice, never quietly dropped. The replay on the three tabs above offers neither a proxy nor a manual exclusion.

!!! warning "A proxy is a choice, not a fact"

    Replacing a holding with a proxy changes what the result means. It no longer says what would have happened to that position; it says what would have happened **if that position had behaved like its substitute** over that episode. That condition is part of the answer, not a footnote to it — a broad index proxying a concentrated holding will understate how that holding would have moved, and no part of the arithmetic can detect the mismatch. The result records which holdings were proxied.

---

## 💡 Interpretation {: #interpretation }

The replay produces a compounded return for the episode, and underneath it a return for each holding it replayed. Read them as a **conditional statement**: *this composition, through those specific dates, with no rebalancing, cash flat — and flat with it every holding the engine left out — and a proxy only where one was chosen*. On a selection of assets there is no composition to compound and nothing is held flat: the per-asset returns stand alone, for the assets that could be replayed.

Its strength is that every number in it happened. The sequence of returns is the one the market delivered — the drawdown path, the clustering of bad days, the speed of the recovery are all real, which is exactly what a distributional summary cannot reproduce. Its weakness is the mirror image: it is **one** episode. It happened once, and the next stress will not be a copy of it.

A replay is therefore not a forecast and not a probability. It is a measurement of exposure against a known event — useful because the event is known, and limited for the same reason.

---

## ⚠️ Limitations {: #limitations }

!!! warning "One episode is one sample"

    Replaying a single historical stretch says what that stretch would do. It does not bound what a future stretch could do, and choosing the worst episode in the record does not make the result a worst case — it makes it the worst case *in the record*.

!!! warning "The composition is fixed at today's"

    Positions opened after the episode, positions since closed, and every change of size in between are absent by construction. The further the replay range lies from today, the more the replayed portfolio is a construct rather than a history.

!!! warning "Returns are taken as they are measured"

    The replay prepares its return series the way the rest of the analysis does, but over the window of its episode and for the assets it replays, each proxy in place of the holding it stands for. Those series share one calendar, built as described under [Data Quality](data-quality.md#alignment-what-missing-data-actually-costs): every date of the window on which at least one of those assets has a quote of its own, kept wherever every one of them can be valued, if need be at a price carried forward from an earlier date. Gaps, carried-forward prices and currency conversion all reach the replay through those series. See [Data Quality](data-quality.md) for what the analysis reports about the series it used.

---

## 🔗 Related {: #related }

- ⚡ **[Hypothetical Shock](hypothetical-shock.md)** — the same question with a chosen scenario instead of a historical one
- 📉 **[Max Drawdown](max-drawdown.md)** — the worst fall along a path, and [how long recovery took](max-drawdown.md#recovery-time)
- 📍 **[Current Drawdown](current-drawdown.md)** — where the portfolio stands today, before any scenario is applied
- 🧩 **[Risk Contribution](risk-contribution.md)** — which holdings carry the risk that an episode would act on
- 🧪 **[Data Quality](data-quality.md)** — the series the replay was run on
