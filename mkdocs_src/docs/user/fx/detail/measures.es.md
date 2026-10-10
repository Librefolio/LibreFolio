# 📐 Medidas

El panel Medidas te indica cómo se movió el tipo de cambio entre dos puntos del gráfico: el cambio, el
cambio en % y la tasa anual.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Panel de medidas FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Realizar una medición

### 📏 Paso 1: Activa el modo de medición

Haz clic en 📏 (**Añadir medición**) en la parte superior derecha del gráfico. El panel **Medidas** debajo del gráfico
se abre y muestra **Activo — haz clic en el gráfico**.

### 📍 Paso 2: Haz clic en el punto de inicio

Una indicación muestra la fecha y el tipo de cambio que seleccionaste; una línea discontinua sigue al puntero.

### 🏁 Paso 3: Haz clic en el punto final

La medición se añade y el modo de medición se desactiva. Las dos fechas se ordenan automáticamente.

??? tip "➕ Todo el periodo en un solo clic — práctico en el móvil"

    El botón **+** de la barra **Medidas** mide el periodo seleccionado desde su primer tipo de cambio hasta el último, sin hacer clic en el gráfico.

---

## 📊 Leer una medición

Cada medición es una tarjeta que muestra sus fechas, el cambio en % y el número de días naturales; también
puedes definir el color y el estilo de su línea. Expándela para cambiar las fechas y ver **Inicio**,
**Fin**, **Δ Abs**, **Δ %** y **Δ%/yr** para el par FX y para cada superposición en el mismo eje.

**Δ%/yr** es la tasa anual (CAGR), donde $d$ son los días naturales entre las dos fechas:

$$
\Delta\%_{yr} = \left(\frac{P_{end}}{P_{start}}\right)^{365/d} - 1
$$

Consulta [Rentabilidades y tasas de crecimiento — Teoría financiera](../../../financial-theory/fundamentals/returns.md)
para rendimientos logarítmicos y capitalización.

---

## 🔁 Varias mediciones

Cada nueva medición se añade junto a las demás, con su propio color; 🗑️ elimina una. Permanecen hasta
que salgas de la página.

---

## 💡 Consejos

- 🔍 **Haz zoom** antes de hacer clic, para acertar en los puntos exactos.
- 📰 Compara el movimiento **antes y después de un evento**, como un anuncio de un banco central.
- ⚠️ Lee **Δ%/yr** con cuidado en periodos cortos: un movimiento del 1 % en 7 días se capitaliza a aproximadamente el 68 % anual.
  Es más significativo en periodos de 30 días o más.
