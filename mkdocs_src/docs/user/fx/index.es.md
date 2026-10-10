# 💱 Tipos de cambio (Cambio de divisas)

LibreFolio convierte tus importes entre divisas con los tipos de cambio que se guardan aquí. Cada par de divisas
descarga sus tipos de cambio de un banco central (ECB, FED, BOE o SNB), o conserva los tipos que introduzcas tú mismo.

---

## 📋 La página de lista de tipos de cambio

Abre **Tipos de cambio** en la barra lateral para ver tus pares de divisas:

<div class="lf-screenshot-carousel" data-carousel="carousel-fx-list" data-carousel-interval="6000" data-show-titles="true" style="margin: 1rem 0 2rem 0;">
    <img class="gallery-img lf-screenshot-carousel-item is-active" data-category="fx" data-name="list" data-title="🔲 Vista de cuadrícula" alt="Página de lista de tipos de cambio (cuadrícula)">
    <img class="gallery-img lf-screenshot-carousel-item" loading="lazy" data-category="fx" data-name="list-table" data-title="📋 Vista de tabla" alt="Página de lista de tipos de cambio (tabla)">
</div>

Cada par muestra sus banderas (p. ej., 🇪🇺 EUR → 🇺🇸 USD), su **último tipo de cambio**, la variación durante el periodo
seleccionado y un minigráfico. Una insignia ✏️ **Manual** marca los pares sin proveedor. Haz clic en un par para abrir
su [página de detalle](detail/index.md).

### 🔀 Tarjetas o tabla

- El conmutador de vista junto a **Añadir par** alterna entre tarjetas y tabla; LibreFolio recuerda tu
  elección.
- En la tabla, las columnas **Δ** muestran la variación durante el último día, durante el periodo y, en periodos
  largos, de 1S a 5A. **Columnas** añade las ocultas, como los **Proveedores** de cada par.
- Selecciona filas para actuar sobre varios pares a la vez, o haz clic derecho en una fila.

### 🔍 Filtrar por divisa

Elige una divisa en **Filtrar por divisa** para listar solo sus pares, y una **Segunda divisa** para reducir
la lista a un par; ✕ borra ambas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="list-filtered" alt="Lista de tipos de cambio filtrada" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 🧰 Acciones de página y de par

- El selector de **periodo** de la parte superior establece el rango de todos los gráficos y variaciones; en la vista de tarjetas,
  **Abs** / **%** muestra todas las tarjetas como tipos o como variación porcentual.
- **Sincronizar todo** descarga los nuevos tipos de cambio ([Sincronización](sync.md)); **Recargar todo** vuelve a leer los
  almacenados. **Configuración** establece la apariencia de cada tarjeta ([Ajustes del gráfico](chart-settings.md)).
- En una tarjeta, ⇄ invierte la dirección mostrada (USD → EUR en lugar de EUR → USD); los botones de la parte inferior
  abren sus propios ajustes del gráfico, **Sincronizar** o **Recargar**, o eliminarla.

!!! warning "Eliminar un par elimina sus tipos de cambio"

    Eliminar un par elimina la configuración de su proveedor **y todos sus tipos de cambio almacenados**, una vez que confirmes.

---

## 🔮 ¿Qué sigue?

- ➕ **[Añadir un par](add-pair.md)** — Crea un par con una ruta directa o en cadena
- 🔄 **[Sincronización](sync.md)** — Descarga tipos de cambio, manualmente o según una programación
- 📊 **[Página de detalle del par](detail/index.md)** — Gráfico, señales, medidas, editor de tipos de cambio y proveedores
- ⚙️ **[Ajustes del gráfico](chart-settings.md)** — Aspecto del gráfico y señales superpuestas
- 🔌 **[Proveedores](providers/index.md)** — Los bancos centrales que LibreFolio lee (ECB, FED, BOE, SNB)
