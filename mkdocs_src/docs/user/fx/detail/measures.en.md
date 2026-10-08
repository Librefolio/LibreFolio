# 📐 Measures

The Measures panel tells you how the rate moved between two points of the chart: the change, the
change in % and the yearly rate.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="FX Measures Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Take a measurement

### 📏 Step 1: Turn on measure mode

Click 📏 (**Add measurement**) at the top right of the chart. The **Measures** panel below the chart
opens and reads **Active — click chart**.

### 📍 Step 2: Click the start point

A hint shows the date and rate you picked; a dashed line follows the pointer.

### 🏁 Step 3: Click the end point

The measurement is added and measure mode turns off. The two dates are put in order for you.

??? tip "➕ The whole period in one click — handy on a phone"

    The **+** button on the **Measures** bar measures the selected period from its first rate to its
    last, without clicking on the chart.

---

## 📊 Read a measurement

Each measurement is a card showing its dates, the change in % and the number of calendar days; you
can also set its line's colour and style. Expand it to change the dates and to see **Start**,
**End**, **Δ Abs**, **Δ %** and **Δ%/yr** for the pair and for each overlay on the same axis.

**Δ%/yr** is the yearly rate (CAGR), with $d$ the calendar days between the two dates:

$$
\Delta\%_{yr} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

See [Returns & Growth Rates — Financial Theory](../../../financial-theory/fundamentals/returns.md)
for log returns and compounding.

---

## 🔁 Several measurements

Each new measurement is added next to the others, in its own colour; 🗑️ removes one. They stay until
you leave the page.

---

## 💡 Tips

- 🔍 **Zoom in** before clicking, to hit the exact points.
- 📰 Compare the move **before and after an event**, such as a central bank announcement.
- ⚠️ Read **Δ%/yr** with care on short periods: a 1 % move in 7 days compounds to about 68 % a year.
  It means most over 30 days or more.
