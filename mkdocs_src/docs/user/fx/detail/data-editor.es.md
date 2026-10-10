# ✏️ Editor de datos e importación CSV

El editor de datos te permite añadir, cambiar y eliminar los tipos de cambio almacenados de un par uno a uno, o cargar muchos
a la vez desde un archivo CSV. Nada se guarda hasta que hagas clic en **Guardar**.

---

## 📝 Abrir el editor

Haz clic en ✏️ (**Editar tipos de cambio**) en el gráfico. El editor se abre debajo del gráfico y los demás paneles se pliegan
mientras editas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Editor de datos FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Muestra los tipos de cambio del periodo seleccionado con su **Fecha**, **Tipo de cambio** y **Estado** (**Original**,
**Editado**, **Eliminado** o **Nuevo**).

- Una fecha marcada con ⚠️ y un número de días no tiene tipo de cambio propio (un fin de semana o un festivo bancario) y
  repite el anterior. El interruptor ⚠️ en la parte superior oculta estos días.
- Haz doble clic en un punto del gráfico (mantén pulsado en móvil) para saltar a su fecha en el editor.

---

## ✍️ Cambiar tipos de cambio

### ➕ Añadir un tipo de cambio

Haz clic en **Añadir fila**: aparece una fila en el día siguiente al último, nunca más tarde que hoy. Cambia su
fecha con el selector de fecha si es necesario y luego escribe el tipo de cambio.

### ✏️ Editar un tipo de cambio

Haz clic en un tipo de cambio y escribe el nuevo valor.

### 🗑️ Eliminar tipos de cambio

Haz clic en 🗑️ en una fila, o selecciona filas y haz clic en la papelera de la parte superior. **Deshacer** recupera una fila hasta que
guardes.

### 💾 Guardar tus cambios

Tus cambios se muestran en el gráfico como una línea **Vista previa** morada. **Guardar (N)** los guarda todos;
**Cancelar** los descarta. Un tipo de cambio debe ser mayor que cero: uno con valor cero, negativo o vacío se omite.

!!! warning "Los datos sincronizados sobrescriben las ediciones manuales"

    Una sincronización posterior de las mismas fechas reemplaza tus valores con los del proveedor. Para tener control
    manual completo, usa un par sin proveedor — consulta [Configuración del proveedor](provider.md).

---

## 📥 Importación CSV

### 🔓 Abrir la ventana de importación

1. En el editor, haz clic en **Importar CSV**.
2. En **Importar datos CSV**, suelta un archivo `.csv` o `.txt`, o pega el texto en el cuadro.
3. Comprueba la dirección en la parte superior y luego haz clic en **Importar (N)**.

Las filas se añaden al editor: revísalas y luego haz clic en **Guardar**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Ventana de importación CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📄 Formato de archivo

Dos columnas, con una fila de encabezado que establece la dirección:

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

| Regla | Detalles |
|------|---------|
| **Separador** | Punto y coma (`;`) |
| **Encabezado** | `date` y la dirección, p. ej. `EUR>USD` |
| **Fechas** | `YYYY-MM-DD` |
| **Tipos de cambio** | Números positivos; `.` o `,` como separador decimal, `_` opcional para separar miles (`1_000.50`) |

### ↔️ Dirección

- `EUR>USD` significa **1 EUR = X USD**; `EUR<USD` es al revés, **1 USD = X EUR**.
- El encabezado debe nombrar las dos divisas de este par, en cualquier orden.
- La barra de la parte superior muestra cómo se leen los tipos de cambio (*Tipos de cambio interpretados como: 1 EUR = X USD*); ⇄ invierte la dirección
  y reescribe el encabezado.
- Un archivo en la dirección opuesta a la de la página se invierte automáticamente: cada tipo de cambio $r$ se convierte en $1/r$.

??? example "📋 Ejemplos — los mismos tipos de cambio escritos en ambas direcciones"

    ```csv
    date;EUR>USD
    2024-01-02;1.1045
    2024-01-03;1.0982
    ```

    ```csv
    date;USD>EUR
    2024-01-02;0.9053
    2024-01-03;0.9106
    ```

    En la página EUR/USD ambos archivos dan los mismos tipos de cambio: `0.9053` se convierte en $1/0.9053 \approx 1.1046$.

### ⚠️ Errores comunes

La ventana de importación marca cada línea incorrecta; solo se importan las líneas válidas.

| Mensaje | Causa | Solución |
|---------|-------|-----|
| **Las divisas del encabezado no coinciden** | Otras divisas en el encabezado, p. ej. `GBP>JPY` en la página EUR/USD | Usa las divisas de este par |
| **Encabezado esperado** o **Faltan columnas obligatorias** | Sin fila de encabezado, o falta una columna | Empieza con una línea como `date;EUR>USD` |
| **Formato de fecha no válido** | La fecha no es `YYYY-MM-DD` | Corrige la fecha |
| **Número no válido** | El tipo de cambio no es un número | Corrige el valor |
| **Fecha duplicada** | La misma fecha aparece dos veces | Mantén una línea por fecha |

??? info "🔀 Cómo se fusionan las filas importadas — cuando el editor ya tiene algunas de las fechas"

    - Una fecha que ya está en el editor toma el tipo de cambio importado (estado **Editado**); una fecha nueva se añade
      (estado **Nuevo**). Las fechas que faltan en el archivo permanecen como están.
    - Las fechas fuera del periodo seleccionado también se guardan, reemplazando cualquier tipo de cambio almacenado en esos días;
      después de guardar, el periodo se amplía para mostrarlas.
