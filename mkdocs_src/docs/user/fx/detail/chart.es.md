# 📉 Gráfico Interactivo

El núcleo de la página de detalle del par: un gráfico completo **potenciado por ECharts** que permite visualizar el historial de tipos de cambio con herramientas interactivas avanzadas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-chart" alt="Gráfico de detalle de divisas" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔀 Modos de visualización

Alterna entre dos modos mediante la barra de herramientas:

- 📈 **Absoluto** — Muestra los valores brutos del tipo de cambio (ej. 1 EUR = 1,0845 USD). Ideal para ver los niveles reales del tipo.
- 📊 **Porcentaje (%)** — Muestra el cambio porcentual desde el primer punto de datos visible. Ideal para comparar movimientos relativos y superponer múltiples señales.

Al cambiar al modo %, todas las señales superpuestas también se recalculan como porcentajes desde sus respectivos puntos de partida.

---

## 🔍 Navegación y zoom

| Acción | Escritorio | Móvil |
|--------|------------|-------|
| **Desplazar** | Clic + arrastrar | Toque + arrastrar |
| **Acercar** | Rueda del mouse hacia arriba | Pellizcar para ampliar |
| **Alejar** | Rueda del mouse hacia abajo | Pellizcar para reducir |
| **Restablecer zoom** | Doble clic | Doble toque |

También puedes usar los **presets temporales** (1S, 1M, 3M, 6M, 1A, 2A) o seleccionar un rango **Personalizado** para acceder rápidamente a períodos específicos.

!!! info "Disponibilidad de datos"
    Si el rango seleccionado excede los datos disponibles, LibreFolio muestra lo que hay. Usa **Sincronizar** para intentar descargar datos más antiguos — pero ten en cuenta que algunos proveedores tienen cobertura histórica limitada.

---

## 💬 Descripción emergente

Pasa el cursor sobre cualquier punto del gráfico para ver:

- 📅 La **fecha**
- 💱 El **tipo de cambio** con precisión completa
- 📊 El **porcentaje de cambio** respecto al punto de datos anterior

---

## 🧰 Barra de herramientas

La barra de herramientas del gráfico ofrece acceso rápido a:

- 📊 **Modo de visualización** — Absoluto / Porcentaje
- ⏱️ **Rango temporal** — 1S, 1M, 3M, 6M, 1A, 2A, Personalizado
- 📈 **[Señales](signals.md)** — Activar superposiciones de indicadores técnicos
- 📏 **[Medidas](measures.md)** — Herramienta de medición entre puntos
- ✏️ **[Editor de datos](data-editor.md)** — Editar puntos de datos individuales
- ⚙️ **[Configuración del gráfico](../chart-settings.md)** — Personalización visual

---

## 🔗 Relacionado

- ⚙️ **[Configuración del gráfico](../chart-settings.md)** — Personalizar colores, grosor de línea, relleno de área, cuadrícula
- 📈 **[Señales](signals.md)** — Superponer indicadores técnicos en el gráfico
