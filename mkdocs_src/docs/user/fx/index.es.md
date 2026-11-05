# 💱 Tipos de cambio (Cambio de divisas)

LibreFolio convierte tus importes entre divisas con los tipos que se guardan aquí. Cada par de divisas
descarga sus tipos de un banco central (ECB, FED, BOE o SNB), o guarda los tipos que introduces tú mismo.

---

## 📋 La página de la lista de FX

Abre **Tipos de cambio** en la barra lateral para ver tus pares de divisas:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vista de cuadrícula de tarjetas" alt="Página de la lista de FX (cuadrícula)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vista de tabla de datos" alt="Página de la lista de FX (tabla)">
</div>

Cada par muestra sus banderas (p. ej. 🇪🇺 EUR → 🇺🇸 USD), su **último tipo**, la variación en el periodo
seleccionado y un minigráfico. Cuando el gráfico agrupa los tipos por semana o por mes porque la
gráfica es demasiado estrecha para tantos días, una insignia **Semanal** o **Mensual** en su esquina
superior izquierda lo indica, como en la [página de detalle](detail/chart.md). Una insignia ✏️ **Manual**
marca los pares sin proveedor. Haz clic en un par para abrir su [página de detalle](detail/index.md).

### 🔀 Tarjetas o tabla

- El interruptor de vista junto a **Añadir par** alterna entre tarjetas y tabla; LibreFolio recuerda tu
  elección.
- En la tabla, las columnas **Δ** muestran la variación del último día, del periodo y, en periodos
  largos, de 1S a 5A. **Columnas** añade columnas ocultas, como los **Proveedores** de cada par.
- Selecciona filas para actuar sobre varios pares a la vez, o haz clic derecho en una fila.

### 🔍 Filtrar por divisa

Elige una divisa en **Filtrar por divisa** para listar solo sus pares, y una **Segunda divisa** para reducir
la lista a un solo par; ✕ borra ambas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Lista de FX filtrada" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧰 Acciones de página y de par

- El selector de **periodo** de la parte superior fija el rango de todos los gráficos y variaciones; en la
  vista de tarjetas, el icono de línea de gráfico (información emergente **Mostrar absoluto**), **%** y el icono de
  calendario (**Rentabilidad móvil**) muestran todas las tarjetas como tipos, como variación % o como
  rentabilidad móvil. La lista se abre en **Abs**; una vez que eliges una vista, se recuerda en este navegador.
- El botón de vista de una tarjeta alterna **%** → **Rentabilidad móvil** → **Abs** y muestra la vista a
  la que pasa. La tarjeta mantiene su propia elección entre recargas hasta que cambias la barra de
  herramientas, lo que restablece la vista de todas las tarjetas. En **Rentabilidad móvil**, una tarjeta
  dibuja la rentabilidad móvil del tipo tal como la tarjeta muestra el par (invertido con ⇄: la
  rentabilidad del tipo invertido), y sobre ella las rentabilidades móviles de los pares FX comparados en
  esa tarjeta. El tipo y su variación en la parte superior se mantienen como están, y con muy poco
  historial la tarjeta muestra un mensaje breve en lugar del gráfico. La ventana es la configurada en
  [Ajustes del gráfico](chart-settings.md).
- Una tarjeta dibuja las comparaciones guardadas en sus [Ajustes del gráfico](chart-settings.md), con otro
  par FX o con un activo. La línea de un activo es su precio en la divisa propia del activo, así que
  compárala en la vista **%**; los precios se cargan una vez para todas las tarjetas que comparan un
  activo.
- **Sincronizar todo** descarga los tipos nuevos ([Sincronización](sync.md)); **Recargar todo** vuelve a
  leer los almacenados. **Configuración** establece el aspecto de cada tarjeta
  ([Ajustes del gráfico](chart-settings.md)). Pasa el cursor sobre cualquiera de los tres durante medio
  segundo para leer qué hace.
- En una tarjeta, ⇄ invierte la dirección mostrada (USD → EUR en lugar de EUR → USD); los botones de la
  parte inferior abren sus propios ajustes del gráfico, lo **sincronizan** o lo **recargan**, o lo eliminan.

!!! warning "Eliminar un par elimina sus tipos"

    Eliminar un par borra la configuración del proveedor **y todos sus tipos almacenados**, una vez que confirmes.

---

## 🔮 ¿Qué viene después?

- ➕ **[Añadir un par](add-pair.md)** — Crea un par con una ruta directa o encadenada
- 🔄 **[Sincronización](sync.md)** — Descarga tipos, de forma manual o programada
- 📊 **[Página de detalle del par](detail/index.md)** — Gráfico, señales, medidas, editor de tipos y proveedores
- ⚙️ **[Ajustes del gráfico](chart-settings.md)** — Aspecto del gráfico y señales superpuestas
- 🔌 **[Proveedores](providers/index.md)** — Los bancos centrales que LibreFolio lee (ECB, FED, BOE, SNB)
