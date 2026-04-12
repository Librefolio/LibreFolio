# ⚙️ Configuración del Gráfico

LibreFolio proporciona un modal de **Configuración del Gráfico** para personalizar la apariencia y el comportamiento de los gráficos de divisas. Esta configuración se aplica tanto a los mini-gráficos en la [Página de Lista de FX](index.md) como al gráfico completo en la [Página de Detalle del Par](detail/index.md).

---

## 🔓 Acceder a la Configuración del Gráfico

Puedes abrir el modal de Configuración del Gráfico desde:
- 📋 La **Página de Lista de FX** — a través del botón de configuración (⚙️) en la barra de herramientas
- 📊 La **Página de Detalle del Par** — a través del botón de configuración del gráfico

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Modal de Configuración del Gráfico" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🎛️ Configuraciones Disponibles

### 🎨 Apariencia

| Configuración | Descripción |
|---------------|-------------|
| **Color de Línea** | Color primario para la línea del gráfico |
| **Ancho de Línea** | Grosor de la línea del gráfico (px) |
| **Relleno de Área** | Activar/desactivar el relleno degradado bajo la línea |
| **Líneas de Cuadrícula** | Mostrar/ocultar líneas de cuadrícula horizontales y verticales |

### 🖱️ Descripción emergente e Interacción

| Configuración | Descripción |
|---------------|-------------|
| **Formato de la descripción emergente** | Número de decimales mostrados en las descripciones emergentes |
| **Cruz** | Activar/desactivar la cruz al pasar el cursor |
| **Zoom** | Configuración de zoom con rueda del ratón y gesto de pellizco |

### 📈 Superposición de Señales

Al usar el gráfico de la página de detalle, puedes configurar qué **indicadores técnicos** se muestran como superposiciones:

#### 🧮 Señales Calculadas

Estas se calculan a partir de los datos propios del par:
- 📉 **EMA** (Media Móvil Exponencial)
- 📊 **MACD** (Convergencia/Divergencia de Medias Móviles)
- 💪 **RSI** (Índice de Fuerza Relativa)
- 📏 **Bandas de Bollinger**

Cada señal se puede activar/desactivar independientemente desde el [Panel de Señales](detail/signals.md).

#### 🔍 Señales Comparativas y Benchmarks

También puedes superponer **comparaciones de benchmarks** para ver cómo se comporta un par en relación con una referencia:
- 📐 **Benchmarks Sintéticos** — Canastas personalizadas o tipos de referencia calculados
- ↔️ **Superposiciones de pares cruzados** — Comparar EUR/USD contra GBP/USD en el mismo gráfico

Para los fundamentos matemáticos, consulta [Indicadores Técnicos](../../financial-theory/technical-analysis/indicators/index.md) y [Benchmarks Sintéticos](../../financial-theory/technical-analysis/synthetic-benchmarks/index.md).

---

## 💾 Persistencia

La configuración del gráfico se almacena en el `localStorage` de tu navegador y se aplica a todos los pares de divisas. Sobrevive entre sesiones — incluso después de cerrar y reabrir el navegador — y solo se perderá si limpias la caché/almacenamiento del navegador o si el almacenamiento expira (depende del navegador, normalmente meses a años).

---
