# 📉 Gráfico Interactivo

El corazón de la página de Detalle del Par: un gráfico completo **impulsado por ECharts** que le permite visualizar el historial de tipos de cambio con potentes herramientas interactivas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Gráfico de Detalle de FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Modos de Vista

Cambie entre dos modos de visualización utilizando la barra de herramientas:

- 📈 **Absoluto** — Muestra los valores originales del tipo de cambio (ej. 1 EUR = 1.0845 USD). Ideal para ver los niveles reales de la tasa.
- 📊 **Porcentaje (%)** — Muestra el cambio porcentual desde el primer punto de datos visible. Ideal para comparar movimientos relativos y superponer múltiples señales.

Al cambiar al modo %, todas las señales superpuestas también se recalculan como porcentajes desde sus respectivos puntos de partida.

---

## 🔍 Navegación y Zoom

| Acción | Escritorio | Móvil |
|--------|---------|--------|
| **Desplazar** | Clic + arrastrar | Tocar + arrastrar |
| **Acercar (Zoom in)** | Rueda del ratón arriba | Pellizcar hacia afuera |
| **Alejar (Zoom out)** | Rueda del ratón abajo | Pellizcar hacia adentro |
| **Restablecer zoom** | Doble clic | Doble toque |

También puede utilizar los **ajustes preestablecidos de rango de tiempo** (1W, 1M, 3M, 6M, 1Y, 2Y) o seleccionar un rango de fechas **Personalizado** para saltar rápidamente a periodos específicos.

!!! info "Disponibilidad de datos"

    Si el rango de tiempo seleccionado excede los datos disponibles, LibreFolio muestra lo que esté disponible. Use **Sync** para intentar obtener datos más antiguos del proveedor; tenga en cuenta que algunos proveedores tienen una cobertura histórica limitada.

---

## 💬 Información emergente

Pase el cursor sobre cualquier punto del gráfico para ver:

- 📅 La **fecha**
- 💱 El **tipo de cambio** con precisión completa
- 📊 El **cambio porcentual** respecto al punto de datos anterior

---

## 🧰 Barra de Herramientas

La barra de herramientas del gráfico proporciona acceso rápido a:

- 📊 **Interruptor de modo de vista** — Absoluto / Porcentaje
- ⏱️ **Rango de tiempo** — 1W, 1M, 3M, 6M, 1Y, 2Y, Personalizado
- 📈 **[Señales](signals.md)** — Interruptor de superposiciones de indicadores técnicos
- 📏 **[Medidas](measures.md)** — Herramienta de medición de clic a clic
- ✏️ **[Editor de Datos](data-editor.md)** — Editar puntos de datos individuales
- ⚙️ **[Configuración del Gráfico](../chart-settings.md)** — Personalización visual

---

## 🔗 Relacionado

- ⚙️ **[Configuración del Gráfico](../chart-settings.md)** — Personalice colores, ancho de línea, relleno de área, cuadrícula
- 📈 **[Señales](signals.md)** — Superponga indicadores técnicos en el gráfico
