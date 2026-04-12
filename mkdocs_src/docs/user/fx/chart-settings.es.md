# ⚙️ Configuración del Gráfico

LibreFolio proporciona un modal de **Configuración del Gráfico** para personalizar la apariencia y el comportamiento de los gráficos de FX. Estos ajustes se aplican tanto a los mini-gráficos de la [página de Lista de FX](index.md) como al gráfico completo de la [página de Detalle del Par](detail/index.md).

---

## 🔓 Acceso a la Configuración del Gráfico

Puede abrir el modal de Configuración del Gráfico desde:

- 📋 La **página de Lista de FX** — a través del botón de configuración (⚙️) en la barra de herramientas
- 📊 La **página de Detalle del Par** — a través del botón de configuración del gráfico

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Modal de Configuración del Gráfico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Configuración Disponible

### 🎨 Apariencia

| Configuración | Descripción |
|---------|-------------|
| **Color de Línea** | Color primario para la línea del gráfico |
| **Ancho de Línea** | Grosor de la línea del gráfico (px) |
| **Relleno de Área** | Activar/desactivar el relleno degradado bajo la línea |
| **Líneas de Cuadrícula** | Mostrar/ocultar las líneas de cuadrícula horizontales y verticales |

### 🖱️ Información Emergente e Interacción

| Configuración | Descripción |
|---------|-------------|
| **Formato de la información emergente** | Número de decimales mostrados en las informaciones emergentes |
| **Cruz** | Activar/desactivar la cruz al pasar el cursor |
| **Zoom** | Ajustes de zoom mediante la rueda del ratón y gestos de pinza |

### 📈 Superposición de Señales

Al utilizar el gráfico de la página de detalle, puede configurar qué **indicadores técnicos** se muestran como superposiciones:

#### 🧮 Señales Calculadas

Estas se computan a partir de los propios datos del par:

- 📉 **EMA** (Exponential Moving Average)
- 📊 **MACD** (Moving Average Convergence Divergence)
- 💪 **RSI** (Relative Strength Index)
- 📏 **Bandas de Bollinger**

Cada señal puede activarse o desactivarse mediante el interruptor de forma independiente desde el [panel de Señales](detail/signals.md).

#### 🔍 Señales Comparativas y Benchmarks

También puede superponer **comparaciones de benchmark** para ver cómo se comporta un par en relación con una referencia:

- 📐 **Benchmarks Sintéticos** — Canastas personalizadas o tasas de referencia computadas
- ↔️ **Superposiciones de pares cruzados** — Comparar EUR/USD frente a GBP/USD en el mismo gráfico

Para los fundamentos matemáticos, consulte [Indicadores Técnicos](../../financial-theory/technical-analysis/indicators/index.md) y [Benchmarks Sintéticos](../../financial-theory/technical-analysis/synthetic-benchmarks/index.md).

---

## 💾 Persistencia

La configuración del gráfico se almacena localmente en el `localStorage` de su navegador y se aplica a todos los pares de divisas. Se mantiene entre sesiones — incluso después de cerrar y volver a abrir el navegador — y solo se perderá si borra la caché/almacenamiento del navegador o si el almacenamiento expira (dependiendo del navegador, normalmente de meses a años).
