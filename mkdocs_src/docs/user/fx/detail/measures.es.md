# 📐 Medidas

El panel de Medidas proporciona una **herramienta de medición entre dos clics** para analizar los movimientos de tipo de cambio entre cualquier par de puntos del gráfico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-measures" alt="Panel de Medidas FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🖱️ Cómo Usarlo

1. Haz clic en el interruptor **Medidas** (📐) en la barra de herramientas del gráfico
2. El panel de medidas se abre debajo del gráfico
3. **Haz clic** en un punto de partida en el gráfico — esto establece la fecha y el tipo de cambio "desde"
4. **Haz clic** en un punto final — esto establece la fecha y el tipo de cambio "hasta"
5. El panel muestra inmediatamente las métricas calculadas entre los dos puntos

---

## 📊 Métricas Calculadas

Para cada medición, el panel muestra:

| Métrica | Descripción | Ejemplo |
|--------|-------------|---------|
| **Intervalo de Fechas** | Fechas Desde → Hasta | 15 ene 2024 → 20 mar 2024 |
| **Días** | Días calendario entre los dos puntos | 65 días |
| **Delta (Δ)** | Cambio absoluto del tipo de cambio | +0.0342 |
| **Porcentaje (%)** | Cambio relativo en porcentaje | +3.12% |
| **Retorno Anualizado** | Retorno anual proyectado basado en el período medido | +17.8% p.a. |

!!! info "📚 Retorno Anualizado"
 El retorno anualizado utiliza la fórmula de **Tasa de Crecimiento Anual Compuesto (CAGR)**. Para una explicación comprensiva que incluye retornos logarítmicos, capitalización y cuándo usar cada método, consulta:

 :material-book-open-variant: **[Retornos & Tasas de Crecimiento — Teoría Financiera](../../../financial-theory/returns.md)**

---

## 🔁 Múltiples Mediciones

Puedes tomar múltiples mediciones en secuencia — cada nuevo par de clics reemplaza la medición anterior. Esto te permite comparar rápidamente movimientos en diferentes ventanas de tiempo.

---

## 💡 Consejos

- 🔍 **Haz zoom** antes de medir para mayor precisión en los puntos de clic.
- 📰 Usa las mediciones para comparar movimientos de tipo de cambio **previa/posterior a un evento** (por ejemplo: antes y después de un anuncio de un banco central).
- ⚠️ El retorno anualizado es más significativo para períodos de **30 días o más** — períodos muy cortos pueden producir cifras anualizadas engañosas.
