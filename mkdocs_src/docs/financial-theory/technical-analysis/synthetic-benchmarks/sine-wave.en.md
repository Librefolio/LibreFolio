# 🌊 Sine Wave

A sine wave benchmark represents **periodic oscillation**. It is the only non-growth benchmark in LibreFolio.

---

## 💡 Financial Meaning

Useful for:

- Modelling **seasonality** (e.g. agricultural commodities, tourism-linked currencies).
- Providing a visual reference for **cyclic patterns** that traders suspect in the data.
- Testing the rendering pipeline with a known analytic waveform.

---

## 🔢 Mathematical Formula

$$
y(t) = A \cdot \sin\!\left(\frac{2\pi t}{T}\right) + y_0 + \text{offset}
$$

where:

- $A$ is the amplitude (peak-to-peak range as % of base value),
- $T$ is the period in days,
- $y_0$ is the base value (first data point),
- $\text{offset}$ is a vertical shift.

---

## ⚙️ Parameters

| Parameter | Key | Default | Description |
|---|---|---|---|
| Amplitude | `amplitude` | 10 | Peak oscillation range as % of base value. |
| Period | `period` | 365 | Full cycle length in days. |
| Offset | `offset` | 0 | Vertical shift as % of base value. |

---

## 🔍 Interpretation

If the actual price roughly tracks the sine reference, the market exhibits a detectable cyclic component at that frequency. Deviations from the sine suggest non-periodic shocks or trend drift. Adjusting the period parameter lets you scan across different cycle lengths — effectively performing a manual version of spectral analysis.

:material-link: [Sine Wave on Wikipedia](https://en.wikipedia.org/wiki/Sine_wave){ target="_blank" }


