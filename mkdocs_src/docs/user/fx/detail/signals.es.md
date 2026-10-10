# 📈 Señales

El panel **Señales** dibuja indicadores técnicos, series de comparación y curvas de benchmarks sintéticos en el
gráfico de FX. LibreFolio calcula los indicadores a partir de los tipos de cambio almacenados del par.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="Panel de señales de FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🛠️ Añadir una señal

1. Haz clic en la barra **Señales** situada encima del gráfico para desplegar el panel.
2. Elige una señal en uno de los tres menús desplegables: **Indicadores técnicos**, **Comparación de datos** o
   **Benchmarks sintéticos**.
3. Ajusta sus parámetros en su tarjeta: el gráfico se actualiza.
4. Arrastra las tarjetas para reordenarlas; 🗑️ elimina una.

Las señales que añadas se guardan con los [ajustes del gráfico](../chart-settings.md) de este par.

---

## 🧮 Indicadores técnicos — 9 para FX

Nueve indicadores funcionan con tipos de cambio. Sigue los enlaces de abajo, o haz clic en 📖 en una tarjeta, para ver las matemáticas
detrás de cada uno.

| Familia | Indicadores |
|---|---|
| 📈 **Tendencia** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Impulso** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [Stochastic RSI](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatilidad** (1) | [Bandas de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

??? info "🤔 ¿Por qué solo 9? — los otros indicadores necesitan más que un tipo de cambio diario"

    Los tipos de cambio tienen un valor por día, sin máximo, mínimo ni volumen. Los otros
    indicadores necesitan esos campos, o miden riesgo tipo cartera, por lo que solo están disponibles en
    [gráficos de activos](../../assets/detail/signals.md). La lista completa está en
    [Indicadores técnicos — Teoría financiera](../../../financial-theory/technical-analysis/indicators/index.md).

### 🔍 Encontrar un indicador

El menú desplegable **Indicadores técnicos** es un árbol agrupado por familia (tendencia, impulso, volatilidad), con
un cuadro de búsqueda en la parte superior: escribe para filtrar todas las familias a la vez. Las teclas de flecha y `Enter` también funcionan.

*Captura de pantalla próximamente: el árbol de indicadores agrupado abierto en el panel de señales de FX.*

---

## 💱 Comparación de datos

- 💱 **Par FX** — otro de tus pares FX, p. ej. GBP/USD junto a EUR/USD. En la lista, 👑 marca el
  par de esta página y 📌 un par ya usado por otra señal.
- ↔️ **Comparación de activos** — el precio de un activo junto al tipo de cambio.

Una tarjeta de comparación tiene botones para sincronizar el par o el activo comparados y para abrir su página. En la vista %
ambas curvas empiezan en 0 %, por lo que sus movimientos se comparan directamente.

## 📐 Benchmarks sintéticos

Curvas de referencia construidas solo a partir de parámetros, sin datos de mercado:
[Crecimiento lineal](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md),
[Crecimiento compuesto](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) y
[Onda sinusoidal](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🎛️ Leer una tarjeta de señal

- 📖 abre la página de teoría del indicador; pasa el cursor sobre un parámetro para obtener ayuda.
- Una insignia cuenta los puntos de datos cargados para la señal.
- Un indicador de carga gira mientras se calcula la señal. Luego, un icono puede informar de un problema — pasa el cursor sobre él para ver
  los detalles:
    - ℹ️ gris — una pequeña advertencia;
    - ⚠️ ámbar — calculada con advertencias, como huecos, un breve precalentamiento o datos que empiezan después del
      período;
    - ⚠️ rojo — no calculada, por ejemplo porque el historial es demasiado corto.

Si una tarjeta informa de datos faltantes, sincronizar el par normalmente rellena el hueco.

---

## 📚 Análisis en profundidad: teoría financiera

La fórmula de cada indicador, su perspectiva de procesamiento de señales (EMA como filtro IIR, SMA como filtro FIR)
y cómo interpretar sus cruces:

:material-book-open-variant: **[Indicadores técnicos — Teoría financiera](../../../financial-theory/technical-analysis/indicators/index.md)**
