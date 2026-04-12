# 📐 Medidas

El panel de Medidas proporciona una **herramienta de medición de clic a clic** para analizar los movimientos del tipo de cambio entre cualquier par de puntos en el gráfico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Panel de Medidas de FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Cómo utilizarlo

1. Haga clic en el interruptor **Medidas** (📏) en la barra de herramientas del gráfico
2. El panel de medidas se abre debajo del gráfico
3. Haga **clic** en un punto de inicio en el gráfico — esto establece la fecha y el tipo de cambio "desde"
4. Haga **clic** en un punto final — esto establece la fecha y el tipo de cambio "hasta"
5. El panel muestra inmediatamente las métricas calculadas entre los dos puntos

---

## 📊 Métricas Calculadas

Para cada medición, el panel muestra:

| Métrica | Descripción | Ejemplo |
|--------|-------------|---------|
| **Rango de Fechas** | Fechas Desde → Hasta | 15 de ene, 2024 → 20 de mar, 2024 |
| **Días** | Días naturales entre los dos puntos | 65 días |
| **Delta (Δ)** | Cambio absoluto del tipo de cambio | +0.0342 |
| **Porcentaje (%)** | Cambio relativo como porcentaje | +3.12% |
| **Retorno Anualizado** | Retorno anual proyectado basado en el período medido | +17.8% p.a. |

!!! info "📚 Retorno Anualizado"

    El retorno anualizado utiliza la fórmula de la **Tasa de Crecimiento Anual Compuesta (CAGR)**. Para obtener una explicación exhaustiva que incluya retornos logarítmicos, capitalización y cuándo utilizar cada método, consulte:

    :material-book-open-variant: **[Retornos y Tasas de Crecimiento — Teoría Financiera](../../../financial-theory/fundamentals/returns.md)**

---

## 🔁 Mediciones Múltiples

Puede realizar múltiples mediciones en secuencia — cada nuevo par de clics reemplaza la medición anterior. Esto le permite comparar rápidamente los movimientos en diferentes ventanas de tiempo.

---

## 💡 Consejos

- 🔍 Haga **zoom** antes de medir para obtener una mejor precisión en los puntos de clic
- 📰 Utilice las mediciones para comparar los movimientos del tipo de cambio **antes y después de un evento** (por ejemplo, antes y después de un anuncio de un banco central)
- ⚠️ El retorno anualizado es más relevante para períodos de **más de 30 días** — los períodos muy cortos pueden producir cifras anualizadas engañosas
