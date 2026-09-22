# ⚡ Hypothetical Shock

A hypothetical shock replaces the historical episode with a chosen one, which makes it possible to test a scenario that the available history never contained.

[Historical Replay](historical-replay.md) asks *what would that episode do to me?* — the movements are real and you only choose the dates. A hypothetical shock asks *what would happen if I decided this?* — you choose the movements. Neither is a forecast, and the difference between them is where the numbers come from.

---

## 🔢 How the Shock Is Computed {: #how-the-shock-is-computed }

You pick one **dimension** to shock along — asset class, sector or geography — and assign a return to its buckets: *technology falls 30%, energy rises 5%*. The analysis then works in two steps.

First, each holding's shock is assembled from its exposures to those buckets:

$$
s_i = \sum_b e_{ib} \cdot \text{shock}_b
$$

where $e_{ib}$ is holding $i$'s exposure to bucket $b$. This matters more than it looks: a holding is rarely *in* a single bucket. A diversified fund spread across several sectors receives an **exposure-weighted blend** of the shocks you configured, not one of them. The per-holding figure you read is already a mixture.

Second, the portfolio impact is the weighted sum of those per-holding shocks, and each holding's contribution is its own term:

$$
r_{shock} = \sum_i w_i \, s_i, \qquad \text{contribution}_i = w_i \, s_i
$$

There is no return history in this calculation. Unlike every other analytic in the section, a hypothetical shock does not read a single past observation: it needs today's weights and today's classifications, and nothing else. The result reports zero observations for exactly that reason.

---

## 🧾 What Happens to What You Did Not Configure {: #what-you-did-not-configure }

A scenario is never complete. You shock technology, and the portfolio also holds bonds, gold and a fund you never thought about. What the analysis does with the rest is the most important thing on this page — and it is **not the same for every dimension**.

| Dimension | What happens to what you did not configure |
|---|---|
| **Sector**, **geography** | You cannot leave it undefined. The scenario is **refused** unless it includes an `Other` bucket, so the remainder moves by an amount **you chose** |
| **Asset class** | An unconfigured bucket receives a shock of **zero**, and the result labels that row *Unconfigured → zero shock* |

The refusal in the first row happens at the door: a sector or geography scenario without an `Other` bucket is rejected **before anything is computed**, so there is never a partial result built on an undeclared residual.

!!! warning "A zero shock is not neutrality — it is a prediction"

    Leaving a holding unshocked does not remove it from the scenario. It states that while equities fall 30%, that holding does **not move**. That is a claim about the world, and in a broad sell-off it is usually a generous one.

    What makes the design defensible is not that it is cautious — it is that the claim is **written down**. The scenario does not quietly assume the rest of the portfolio stands still; it records, for every holding and every bucket, that a zero was applied because nothing was configured. The assumption is still an assumption. It just is not a hidden one.

The asymmetry between the dimensions is worth knowing rather than judging: on sector and geography you are **forced** to state the residual, on asset class you are not. Which one you are working in decides what you have to check — and if you are shocking by asset class, the thing to check is whether anything came back as unconfigured.

---

## 🔍 Reading the Audit {: #reading-the-audit }

Every holding's impact can be expanded into a per-bucket audit, which is where a scenario stops being something you believe and becomes something you verify. Each row reports:

| Column | What it tells you |
|---|---|
| Exposure bucket | Which bucket of the chosen dimension this row is about |
| Exposure | How much of the holding sits in that bucket |
| Applied bucket | Which bucket's shock was actually used — often, but not always, the same one |
| Shock | The return applied |
| Contribution | That shock scaled by the exposure |
| Rule | **How** the applied bucket was chosen |

The last column is the one to read first, because two holdings can show the same shock for entirely different reasons and only the rule tells them apart. Six rules exist, and on the geography dimension they form a cascade that is tried in order:

| Rule | When a row carries it |
|---|---|
| **Direct** | The holding's own bucket is one you configured — the ordinary case on asset class and sector |
| **Country** | Geography, first step: you configured **that country** itself |
| **Geography group** | Geography, second step: not the country, but a **group that contains it**, such as a regional bucket |
| **Other** | Geography, last step — and the sector equivalent: nothing above matched, so the mandatory residual applied |
| **Missing metadata → Other** | The holding's classification was unavailable, so it was treated as `Other` at 100% |
| **Unconfigured → zero shock** | Asset class only: the bucket was never configured, and zero was applied |

Reading down that list tells you how far from your intention a shock travelled before it landed. A *Country* row is the scenario you wrote; an *Other* row is the residual catching something you did not name; a *Missing metadata* row is a classification problem wearing the same clothes.

!!! info "Ambiguity is refused, not resolved"

    A country can belong to more than one group you configured — a holding in a country covered by two overlapping regional buckets has no single correct shock. Rather than picking one and reporting a number, the analysis **stops and reports the conflict**, naming the country and the groups that collided. It is the same principle as the residual bucket, applied to a case most users would never anticipate: where the scenario is genuinely undetermined, the answer is not a value.

---

## 🏷️ When the Classification Is Missing {: #when-the-classification-is-missing }

Sector and geography shocks depend on knowing what each holding is exposed to. When that metadata is unavailable, the holding is not dropped and not guessed at: it is treated as **`Other` at 100%**, which is why those two dimensions require the `Other` bucket in the first place. The holding is flagged, so the fallback is visible where it happened.

!!! info "The coverage figure on this analytic is not about data density"

    Elsewhere in the section, coverage describes how densely a period was sampled — see [Data Quality](data-quality.md). A hypothetical shock reads no history at all, so on this analytic the coverage figure carries something different: the share of the scope that was classified from **real metadata** rather than falling back to `Other`. A low figure does not mean thin prices; it means much of the scenario landed on the residual bucket instead of the buckets you configured.

---

## 💡 Interpretation {: #interpretation }

The result is a single-period, linear statement: *if these movements happened, at once, to a portfolio composed as it is today, the impact would be this.*

Each word in that sentence is load-bearing.

- **Single period.** There is no path. The arithmetic gives an endpoint, not a sequence, so nothing about the journey to it can be read from the result — no drawdown along the way, no [recovery time](max-drawdown.md#recovery-time), no order of events.
- **Linear.** The impact is exactly the weighted sum of what you specified. There are no second-order effects, no feedback, no contagion from one bucket into another.
- **No correlations.** This is the sharpest difference from the rest of the section. [Correlation](correlation.md) and [Risk Contribution](risk-contribution.md) derive how holdings move together from history; a hypothetical shock does not consult that at all. If you configure technology falling and bonds flat, they do exactly that, however they have behaved together in the past. The co-movements in the scenario are the ones **you** asserted.

The cash share is not shocked: it contributes nothing to the impact, so a portfolio holding cash sees the result scaled down by the invested fraction alone. For cash that is a far smaller assumption than for an unconfigured holding — but it is the same mechanism.

Used well, this is the tool for a question history cannot answer, because the scenario you want to test never happened. Used carelessly, it is a way to obtain any number at all: the output can only be as disciplined as the shocks put in, and nothing in the arithmetic will tell you a scenario is implausible.

---

## ⚠️ Limitations {: #limitations }

!!! warning "It cannot contradict you"

    Every other metric in this section is constrained by data. This one is constrained by your judgement alone: it will faithfully compute the impact of an internally inconsistent scenario — one where correlated assets move in opposite directions, or where a shock is far outside anything that has ever occurred — without any signal that something is off.

!!! warning "It says nothing about likelihood"

    The impact is conditional on the scenario happening exactly as specified. The analysis assigns no probability to that, and a larger impact from a more extreme scenario is not evidence that the scenario is more likely. Comparing two shocks compares two assumptions, not two risks.

!!! warning "The composition is today's"

    Like [Historical Replay](historical-replay.md), the shock is applied to the portfolio as it stands now. It is a statement about current exposure, not about anything that was held before.

---

## 🔗 Related {: #related }

- ⏮️ **[Historical Replay](historical-replay.md)** — the same structure with a real episode instead of a chosen one
- 🧩 **[Risk Contribution](risk-contribution.md)** — which holdings carry the risk, derived from history rather than asserted
- 🔗 **[Correlation](correlation.md)** — the co-movements a hypothetical shock deliberately does not use
- 📉 **[Max Drawdown](max-drawdown.md)** — the path-aware view a single-period shock cannot produce
- 🧪 **[Data Quality](data-quality.md)** — what coverage means on the analytics that do read history
