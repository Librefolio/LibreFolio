# 📈 Señales

El panel de señales te permite superponer **indicadores técnicos**, **series de comparación** y **curvas benchmark** en el gráfico FX. Los indicadores se calculan en el servidor mediante la **plataforma de plugins de señales** del backend de LibreFolio a partir del historial de tipos almacenado del par — el navegador solo renderiza los resultados.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-signals" alt="FX Signals Panel" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🧮 Señales disponibles

Las señales se organizan en **tres categorías**, cada una con su propio menú desplegable en la parte superior del panel: **Indicadores técnicos**, **Comparación de datos** y **Benchmarks sintéticos**.

### 📉 Indicadores técnicos — 9 plugins compatibles con FX

De los 22 plugins de indicadores del backend, **9 se ejecutan sobre los tipos de cierre FX**. Las matemáticas de cada indicador residen en la sección de Teoría financiera — sigue los enlaces de abajo, o haz clic en el icono 📖 de cualquier tarjeta de señal para ir directamente a su página de teoría.

| Familia | Indicadores |
|---|---|
| 📈 **Tendencia** (3) | [EMA](../../../financial-theory/technical-analysis/indicators/ema.md) · [SMA](../../../financial-theory/technical-analysis/indicators/sma.md) · [KAMA](../../../financial-theory/technical-analysis/indicators/kama.md) |
| ⚡ **Momentum** (5) | [RSI](../../../financial-theory/technical-analysis/indicators/rsi.md) · [MACD](../../../financial-theory/technical-analysis/indicators/macd.md) · [ROC](../../../financial-theory/technical-analysis/indicators/roc.md) · [RSI estocástico](../../../financial-theory/technical-analysis/indicators/stochastic-rsi.md) · [PPO](../../../financial-theory/technical-analysis/indicators/ppo.md) |
| 🌊 **Volatilidad** (1) | [Bandas de Bollinger](../../../financial-theory/technical-analysis/indicators/bollinger-bands.md) |

!!! info "¿Por qué solo 9?"

    Los tipos FX tienen un único valor por día — no hay máximo, mínimo ni volumen. Los
    13 plugins restantes necesitan esos campos adicionales (o calculan métricas de riesgo
    de cartera) y están disponibles, en cambio, en los [gráficos de activos](../../assets/detail/signals.md).
    El inventario completo se encuentra en
    [Indicadores técnicos — Teoría financiera](../../../financial-theory/technical-analysis/indicators/index.md).

### 💱 Comparación de datos

Superposiciones calculadas en el navegador que normalizan otra serie sobre el mismo gráfico:

- 💱 **Par FX** — superpone otro par configurado (p. ej., comparar EUR/USD con GBP/USD); los pares ya seleccionados por otra señal se marcan con 📌, y el par de la página actual lleva 👑
- ↔️ **Comparación de activos** — superpone el rendimiento de un activo junto al tipo de cambio

### 📐 Benchmarks sintéticos

**Curvas de referencia matemáticas** calculadas en el navegador y generadas puramente a partir de parámetros — no se necesitan datos de mercado: [Crecimiento lineal](../../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Crecimiento compuesto](../../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md) y [Onda sinusoidal](../../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md).

---

## 🔍 Encontrar un indicador

El menú desplegable de indicadores es un **árbol plegable agrupado por familia** (tendencia, momentum, volatilidad), con un cuadro de búsqueda en la parte superior — escribe para filtrar entre todas las familias a la vez; las flechas, `→`/`←` y `Enter` navegan por el árbol.

*Próximamente: captura de pantalla del árbol de indicadores agrupado abierto en el panel de señales FX.*

---

## 🎛️ Tarjetas de señal

Cada señal añadida se convierte en una tarjeta que muestra:

- 📖 Un **icono de documentación** que enlaza con la página de Teoría financiera del indicador
- 🎚️ **Parámetros integrados** (período, período de señal, …) — algunos elementos de información emergente contienen fórmulas LaTeX renderizadas con KaTeX
- 🏷️ Una **insignia de datos** con el número de puntos del historial de tipos (📈) cargados
- 🗑️ Botón de eliminar; arrastra las tarjetas para reordenar las superposiciones

Un pequeño **spinner** aparece en cada tarjeta mientras la petición al backend está en curso. Tras la carga, un icono de color informa de los **diagnósticos** por señal — pasa el cursor sobre él para ver los detalles: ℹ️ aviso (gris) y ⚠️ advertencia (ámbar) cuando la señal se calculó con salvedades (huecos de datos, calentamiento incompleto, datos que comienzan después del rango del gráfico), 🔴 error (rojo) cuando no se pudo calcular en absoluto (historial insuficiente, campos faltantes). Si una tarjeta informa de datos faltantes, sincronizar el par suele rellenar el hueco.

---

## 🛠️ Cómo usar

1. Haz clic en el interruptor **Señales** (📈) en la barra de herramientas del gráfico
2. El panel de señales se abre debajo del gráfico
3. Añade señales desde los tres menús desplegables de categoría (Indicadores técnicos, Comparación de datos, Benchmarks sintéticos)
4. Ajusta los parámetros de cada señal directamente en su tarjeta
5. Las señales se renderizan como superposiciones directamente en el gráfico

---

## 🧠 Exportación con IA

El botón **Exportación con IA** (:material-brain:) de la barra de herramientas de la página ofrece dos tareas
FX:

- **Análisis de par FX**
- **Impacto de la exposición FX**

La instantánea del backend utiliza el par de divisas canónico de la página, el rango seleccionado,
la divisa objetivo, el historial de tipos y los resultados compartidos de señales técnicas. Para el
Impacto de la exposición FX, la exposición se limita a las divisas de efectivo y a las divisas de
negociación de posiciones o de valoración directamente vinculables al par; **no** examina
fondos ni emisores para inferir una exposición cambiaria oculta. Consulta
[Exportación con IA FX](../../ai-export/fx.md) o la
[descripción general de la Exportación con IA](../../ai-export/index.md).

---

## 📚 A fondo: Teoría financiera

Para un tratamiento matemático exhaustivo de cada indicador — incluyendo fórmulas, equivalentes de procesamiento de señales e interpretación práctica:

:material-book-open-variant: **[Indicadores técnicos — Teoría financiera](../../../financial-theory/technical-analysis/indicators/index.md)**

Esta página de referencia cubre:

- 🔢 Las **fórmulas matemáticas** que hay detrás de cada indicador
- 🎛️ Los equivalentes de **procesamiento de señales** (EMA = filtro IIR, SMA = filtro FIR, etc.)
- ⚡ La intuición de **"rápido vs lento"** en términos de frecuencias de corte del filtro
- 📈 **Ejemplos prácticos** de detección de cruces e identificación de tendencias
