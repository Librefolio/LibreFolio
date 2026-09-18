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

An episode from 2008 cannot be replayed on a fund launched in 2019: there are no returns to apply. Rather than filling the gap with an assumption, the analysis **refuses to run** and asks for a decision. Two are available, and both are recorded in the result:

**Substitute a proxy.** Another asset's return series stands in for the one with no history.

!!! warning "A proxy is a choice, not a fact"

    Replacing a holding with a proxy changes what the result means. It no longer says what would have happened to that position; it says what would have happened **if that position had behaved like its substitute** over that episode. That condition is part of the answer, not a footnote to it — a broad index proxying a concentrated holding will understate how that holding would have moved, and no part of the arithmetic can detect the mismatch. The result records which holdings were proxied.

**Exclude the holding.** The position is dropped from the replay — but its weight is not. The excluded weight is moved into the cash share, which means it is replayed as **earning exactly zero** for the whole episode.

That treatment is worth a moment. Excluding a holding does not make the portfolio smaller; it makes that fraction of the portfolio flat. In an episode where everything fell, a 10% position treated as flat is an implicit claim that it would have been the best thing you owned. The exclusion is recorded in the result with its weight, precisely because the choice is not neutral.

---

## 💡 Interpretation {: #interpretation }

The replay produces a compounded return for the episode, and per-holding returns underneath it. Read them as a **conditional statement**: *this composition, through those specific dates, with no rebalancing, cash flat, and whatever proxies or exclusions were declared*.

Its strength is that every number in it happened. The sequence of returns is the one the market delivered — the drawdown path, the clustering of bad days, the speed of the recovery are all real, which is exactly what a distributional summary cannot reproduce. Its weakness is the mirror image: it is **one** episode. It happened once, and the next stress will not be a copy of it.

A replay is therefore not a forecast and not a probability. It is a measurement of exposure against a known event — useful because the event is known, and limited for the same reason.

---

## ⚠️ Limitations {: #limitations }

!!! warning "One episode is one sample"

    Replaying a single historical stretch says what that stretch would do. It does not bound what a future stretch could do, and choosing the worst episode in the record does not make the result a worst case — it makes it the worst case *in the record*.

!!! warning "The composition is fixed at today's"

    Positions opened after the episode, positions since closed, and every change of size in between are absent by construction. The further the replay range lies from today, the more the replayed portfolio is a construct rather than a history.

!!! warning "Returns are taken as they are measured"

    The replay uses the same prepared return series as the rest of the analysis, over the intersection of the calendars available for the holdings involved. Gaps, carried-forward prices and currency conversion all reach the replay through those series. See [Data Quality](data-quality.md) for what the analysis reports about the series it used.

---

## 🔗 Related {: #related }

- ⚡ **[Hypothetical Shock](hypothetical-shock.md)** — the same question with a chosen scenario instead of a historical one
- 📉 **[Max Drawdown](max-drawdown.md)** — the worst fall along a path, and [how long recovery took](max-drawdown.md#recovery-time)
- 📍 **[Current Drawdown](current-drawdown.md)** — where the portfolio stands today, before any scenario is applied
- 🧩 **[Risk Contribution](risk-contribution.md)** — which holdings carry the risk that an episode would act on
- 🧪 **[Data Quality](data-quality.md)** — the series the replay was run on
