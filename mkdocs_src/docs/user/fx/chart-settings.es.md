# ⚙️ Configuración de gráficos

El modal de **Configuración de gráficos** personaliza la apariencia de los gráficos y las señales superpuestas. El mismo modal se utiliza tanto en la página de [Lista FX](index.md) como en la de [Activos](../assets/index.md), con **configuración independiente por ámbito** — cambiar los valores predeterminados de FX nunca afecta a los gráficos de activos, y viceversa.

---

## 🔓 Acceso a la configuración de gráficos

El modal se abre desde las páginas de lista, en dos variantes:

- 🌐 **Global** — el botón de configuración (⚙️) de la barra de herramientas de la página de lista. Esta configuración se convierte en la predeterminada para todos los gráficos del ámbito; aplicarla reemplaza todas las personalizaciones por tarjeta (el modal te advierte de ello).
- 🎯 **Local** — el botón de configuración (⚙️) de cualquier tarjeta de par o activo. Esta configuración solo anula la global para esa tarjeta.

!!! note "Las páginas de detalle usan paneles en línea en su lugar"

    En la [página de Detalle del Par](detail/index.md) (y en las páginas de detalle de activos), el botón ⚙️
    alterna un **panel de estética** en línea y el botón 📈 alterna el
    **panel de señales** en línea: la misma configuración, el mismo almacenamiento por elemento, sin modal.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="chart-settings" alt="Chart Settings Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 👀 Vista previa en vivo

El modal siempre muestra un **gráfico de vista previa** con un interruptor Abs/%, para que veas el efecto de cada cambio antes de aplicarlo:

<div class="screenshot-container" style="max-width: 620px; margin: 1rem auto;">
 <img class="gallery-img" data-category="assets" data-name="chart-settings" alt="Chart settings modal with the live preview">
</div>

- 🌐 **Modo global** — la vista previa dibuja una curva de demostración sintética. Los indicadores del backend no pueden ejecutarse en el navegador, por lo que el modal pide al servidor que los calcule en vivo sobre esa curva: lo que ves coincide con lo que mostrarán los gráficos reales.
- 🎯 **Modo local** — la vista previa usa los **datos reales de precio** de la tarjeta. Los indicadores del backend muestran la última configuración aplicada; un banner te recuerda que pulses Aplicar para actualizarlos.

---

## 🎛️ Configuración disponible

### 🎨 Apariencia

| Configuración | Descripción |
|---------|-------------|
| **Colores de línea base** | Colorea la línea de verde por encima / rojo por debajo de la línea base |
| **Relleno de área** | Relleno degradado bajo la línea |
| **Líneas de cuadrícula** | Cuadrícula horizontal discontinua |
| **Degradado de datos obsoletos** | Desvanece los datos obsoletos hacia el fondo |
| **Escala del eje Y** | Automática, Incluir 0, o un rango mínimo/máximo personalizado |

### 📈 Señales superpuestas

El modal gestiona las mismas señales superpuestas que el [panel de Señales](detail/signals.md) de la página de detalle, añadidas desde tres menús desplegables por categoría:

- 🧮 **Indicadores técnicos** — el catálogo de plugins del backend para el ámbito actual: **9 indicadores compatibles con FX** aquí, 22 en el ámbito de Activos. El menú desplegable es un árbol con buscador agrupado por familia (tendencia, impulso, volatilidad, …). Las matemáticas que hay detrás de cada indicador se explican en [Indicadores técnicos — Teoría financiera](../../financial-theory/technical-analysis/indicators/index.md).
- ↔️ **Comparación de datos** — superponer otro par FX configurado o un activo en el mismo gráfico.
- 📐 **Benchmarks sintéticos** — curvas de referencia generadas por parámetros ([Lineal](../../financial-theory/technical-analysis/synthetic-benchmarks/linear.md), [Compuesta](../../financial-theory/technical-analysis/synthetic-benchmarks/compound.md), [Onda senoidal](../../financial-theory/technical-analysis/synthetic-benchmarks/sine-wave.md)). Son matemáticas puras — no cestas personalizadas ni datos de mercado.

Cada señal configurada se convierte en una tarjeta con parámetros integrados, un enlace 📖 a su página de teoría y diagnósticos por señal una vez que se ha calculado.

---

## 💾 Persistencia

La configuración de gráficos se guarda localmente en el `localStorage` de tu navegador, por separado para los ámbitos de FX y Activos, con anulaciones por tarjeta sobre la configuración predeterminada del ámbito. Sobreviven entre sesiones — incluso después de cerrar y volver a abrir el navegador — y solo se perderán si borras la caché o el almacenamiento del navegador, o si el almacenamiento caduca (depende del navegador; normalmente de meses a años).
