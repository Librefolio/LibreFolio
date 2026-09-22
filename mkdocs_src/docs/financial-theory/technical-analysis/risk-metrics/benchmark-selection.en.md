# 🎯 Benchmark Selection

Every relative figure carries an invisible passenger: the thing it was measured against. "The portfolio beat the market by three points" is not a statement about the portfolio — it is a statement about the portfolio **and** whatever was called "the market". Change the second term and the verdict changes with it, without a single position having moved.

This page is about that second term. The choice of comparison is not a display preference applied after the analysis: it is part of the result.

---

## 🔢 What "Relative" Means {: #what-relative-means }

Given a primary return series $r_p$ and a comparison series $r_b$ observed on the same dates, LibreFolio derives the relative figures from the pair.

**Active return** is the difference between the two holding-period returns, each compounded over the shared window:

$$\text{Active} = \left[ \prod_{t=1}^{N} (1 + r_{p,t}) - 1 \right] - \left[ \prod_{t=1}^{N} (1 + r_{b,t}) - 1 \right]$$

It is a difference of compounded returns over the window actually shared by the two series — not an annualised figure, and not a ratio.

**Beta** measures how strongly the primary series responded to the comparison one:

$$\beta = \frac{\mathrm{Cov}(r_p, r_b)}{\mathrm{Var}(r_b)}$$

The denominator is the key to the whole page: beta is the covariance **divided by the variance of the benchmark**. Everything the benchmark does — or fails to do — propagates into the figure.

**Correlation** is computed with the same estimator as the [correlation matrix](correlation.md), and answers whether the comparison is even relevant: a beta measured against something the portfolio does not track describes a relationship that is not there.

---

## 💡 Interpretation {: #interpretation }

The three figures answer different questions and are meant to be read together.

| Figure | Question it answers |
|---|---|
| Active return | Did the portfolio end the shared window ahead of or behind the comparison? |
| Beta | How amplified was the portfolio's response to the comparison's movements? |
| Correlation | Was the comparison a meaningful reference at all? |

Correlation comes first in practice. Active return and beta remain arithmetically well-defined against a comparison the portfolio ignores completely, and they are meaningless there — a low correlation is the signal that the benchmark was the wrong question, not that the portfolio was the wrong answer.

### 🧭 Why the Choice Is Already Half the Verdict {: #why-the-choice-is-already-half-the-verdict }

A single global equity portfolio compared against a broad world index, against a domestic index, and against a bond fund will produce three different active returns, three different betas, and three different impressions — from the same positions over the same dates. None of the three is a measurement error. They answer three different questions, and the question was chosen when the benchmark was chosen.

The practical consequence is a comparability rule: **two relative figures can be compared with each other only if they were measured against the same benchmark**. A beta is not a property of a portfolio; it is a property of a portfolio *and* a reference. LibreFolio records the comparison asset in the result's own metadata precisely so that a figure can never be separated from the reference that produced it.

---

## 🧮 What Can Serve as a Benchmark {: #what-can-serve-as-a-benchmark }

The comparison is not free-form. The analysis takes a **real asset that exists in your data** as its reference, identified explicitly, and three things follow from that.

**It must exist.** A comparison against an unknown asset is not silently dropped or replaced by a default: the analytic returns no value, reporting invalid parameters and naming the asset that was requested.

**It must have a usable price history.** The benchmark's series is prepared exactly like the positions under analysis, on the same shared calendar and in the same target currency. If no usable series can be built for it, the result is unavailable rather than approximate.

**It must move.** Beta divides by the variance of the comparison series, so a reference that never moves has no variance to divide by: beta comes back undefined, correlation with it, and both raise an explicit warning rather than a number. This is why a flat reference — a constant, a hypothetical fixed rate of return — cannot function as a benchmark here. The constraint is not a policy that could be waived; it is the arithmetic of the ratio.

!!! info "A benchmark is not a threshold"

    The comparison answers "compared to what?", not "is this good?". A portfolio that lags a rising benchmark and one that falls less than a collapsing benchmark both produce a figure; neither figure knows whether the investor should be satisfied. That judgement needs the objective, which lives outside the metric.

---

## 📏 The Shared Window {: #the-shared-window }

Two series rarely cover exactly the same dates, so the comparison is computed on the **intersection** of the two calendars: only dates present in both contribute.

Three consequences are published with the result.

**A minimum applies.** Below 20 shared observations the comparison is not computed at all: the result comes back unavailable with an insufficient-history reason carrying both the number of shared observations found and the number required. A benchmark that barely overlaps your history produces no figure instead of a fragile one.

**Coverage is reported.** The result records what fraction of the primary series' own dates survived the intersection — that is, how much of your history the chosen reference was actually able to cover. A benchmark launched halfway through your holding period does not silently compare half a period; it says so.

**The annualisation factor is re-measured on the shared window.** Because the intersection is generally shorter and sparser than the full analysis window, any annualised quantity in the comparison is scaled by a factor measured on the common sample rather than inherited from the wider analysis — the same observed-factor logic described in [Observed Annualization](observed-annualization.md), applied to the overlap.

---

## ⚠️ Limitations {: #limitations }

!!! warning "The benchmark is a choice, and the choice is not neutral"

    Because both the beta and the sign of the active return depend on the reference, a comparison chosen after seeing the results is not a measurement — it is a narrative. The honest sequence is to decide what the portfolio is trying to track *before* asking how it performed against it.

!!! warning "Relative figures do not stack"

    Betas and active returns measured against different references belong to different scales. Comparing one asset's beta against a domestic index with another asset's beta against a world index produces a comparison of two unrelated numbers that happen to share a name.

!!! warning "The two sides are not always the same kind of return"

    The comparison asset always contributes the return of its own price series, while the primary side keeps the return basis of what is being analysed — an asset or a whole portfolio. The result records which basis was used on the primary side, and it is worth checking before reading a small active return as meaningful.

!!! warning "A shared calendar hides what it discards"

    Only dates present in both series are compared. If the reference is missing precisely during the turbulent stretch that matters most, those dates leave the comparison entirely, and the remaining figure is calmer than the period it claims to describe. The coverage figure is what makes that loss visible — read it before reading the beta.

---

## 🔗 Related {: #related }

- 📈 **[Beta & Active Return](beta-active-return.md)** — the two figures this choice determines
- 🔗 **[Correlation](correlation.md)** — whether the chosen reference is relevant at all
- 📅 **[Observed Annualization](observed-annualization.md)** — why the factor is re-measured on the overlap
- 🧪 **[Data Quality](data-quality.md)** — what the shared calendar drops, and how it is reported
