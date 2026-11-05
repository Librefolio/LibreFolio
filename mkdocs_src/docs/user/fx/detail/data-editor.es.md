# ✏️ Editor de datos e importación CSV

El editor de datos te permite añadir, cambiar y eliminar los tipos de cambio almacenados de un par uno a uno, o cargar muchos de ellos a la vez desde un archivo CSV. No se guarda nada hasta que hagas clic en **Guardar**.

---

## 📝 Abrir el editor

Haz clic en ✏️ (**Editar tipos de cambio**) en el gráfico. El editor se abre debajo del gráfico y los demás paneles se pliegan mientras editas.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Editor de datos de divisas" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

Muestra los tipos de cambio del periodo seleccionado con su **Fecha**, **Tipo de cambio** y **Estado** (**Original**, **Editado**, **Eliminado** o **Nuevo**).

- Una fecha marcada con ⚠️ y con un número de días no tiene un tipo de cambio propio (un fin de semana o un día festivo) y repite el tipo de cambio anterior. El interruptor ⚠️ de la parte superior oculta esos días.
- Haz doble clic en un punto del gráfico (pulsación larga en móvil) para saltar a su fecha en el editor.

---

## ✍️ Cambiar tipos de cambio

### ➕ Añadir un tipo de cambio

Haz clic en **Añadir fila**: aparece una fila en el día siguiente al último, nunca posterior a hoy. Cambia su fecha con el selector de fechas si es necesario y, después, escribe el tipo de cambio.

### ✏️ Editar un tipo de cambio

Haz clic en un tipo de cambio y escribe el nuevo valor.

### 🗑️ Eliminar tipos de cambio

Haz clic en 🗑️ de una fila, o selecciona filas y haz clic en la papelera de la parte superior. **Deshacer** recupera una fila hasta que guardes.

### 💾 Guardar los cambios

Tus cambios se muestran en el gráfico como una línea **Vista previa** de color morado. **Guardar (N)** los guarda todos; **Cancelar** los descarta. Un tipo de cambio debe ser mayor que cero: se omite un tipo de cambio cero, negativo o vacío. Un tipo de cambio que la base de datos no puede conservar —más de 14 dígitos antes del separador decimal, o por debajo de 0.0000000001— se rechaza al guardar y no se almacena. El límite se aplica al tipo de cambio tal como se almacena: LibreFolio ordena alfabéticamente las divisas de cada par, por lo que en la página USD/EUR se aplica a 1 ÷ el tipo de cambio que escribes.

Si el servidor rechaza algunos de tus tipos de cambio, como uno demasiado grande o demasiado pequeño para almacenarlo, guarda los demás. A continuación, un aviso enumera hasta cinco fechas rechazadas, cada una con su motivo, y cuenta el resto; permanece 20 segundos, para que puedas anotarlas y volver a introducirlas. Si rechaza el guardado completo, por ejemplo, porque una fecha es posterior a mañana, o porque no se puede almacenar ninguno de los tipos de cambio, no se guarda nada: el mensaje explica el motivo y el editor permanece abierto con tus cambios.

!!! warning "Los datos sincronizados sobrescriben las ediciones manuales"

    Una sincronización posterior de las mismas fechas sustituye tus valores por los del proveedor. Para tener un control manual completo, usa un par sin proveedor — consulta [Configuración del proveedor](provider.md).

---

## 📥 Importación CSV

### 🔓 Abrir la ventana de importación

1. En el editor, haz clic en **Importar CSV**.
2. En **Importar datos CSV**, suelta un archivo `.csv` o `.txt`, o pega el texto en el cuadro.
3. Comprueba la dirección en la parte superior y, después, haz clic en **Importar (N)**.

Las filas se añaden al editor: revísalas y, después, haz clic en **Guardar**.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
    <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Modal de importación CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 📄 Formato del archivo

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
| **Tipos de cambio** | Números positivos; `.` o `,` como separador decimal, `_` opcional para los miles (`1_000.50`) |

### ↔️ Dirección

- `EUR>USD` significa **1 EUR = X USD**; `EUR<USD` es al contrario, **1 USD = X EUR**.
- El encabezado debe nombrar las dos divisas de este par, en cualquier orden.
- La barra superior muestra cómo se interpretan los tipos de cambio (*Tipos de cambio interpretados como: 1 EUR = X USD*); ⇄ invierte la dirección y reescribe el encabezado.
- Un archivo en la dirección opuesta a la página se invierte automáticamente: cada tipo de cambio $r$ pasa a ser $1/r$.

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

    En la página EUR/USD ambos archivos dan los mismos tipos de cambio: `0.9053` pasa a ser $1/0.9053 \approx 1.1046$.

### ⚠️ Errores comunes

La ventana de importación marca cada línea incorrecta; solo se importan las líneas válidas.

| Mensaje | Causa | Solución |
|---------|-------|-----|
| **Las divisas del encabezado no coinciden** | Otras divisas en el encabezado, p. ej. `GBP>JPY` en la página EUR/USD | Usa las divisas de este par |
| **Se esperaba un encabezado** o **Faltan columnas obligatorias** | No hay fila de encabezado o falta una columna | Empieza con una línea como `date;EUR>USD` |
| **Formato de fecha no válido** | La fecha no es `YYYY-MM-DD` | Corrige la fecha |
| **Número no válido** | El tipo de cambio no es un número | Corrige el valor |
| **Fecha duplicada** | La misma fecha aparece dos veces | Mantén una línea por fecha |

??? info "🔀 Cómo se combinan las filas importadas — cuando el editor ya tiene algunas de las fechas"

    - Una fecha que ya está en el editor toma el tipo de cambio importado (**Editado**); una fecha nueva se añade con el estado **Nuevo**. Las fechas que faltan en el archivo se quedan como están.
    - Las fechas fuera del periodo seleccionado también se guardan, sustituyendo cualquier tipo de cambio almacenado en esos días; tras guardar, el periodo se amplía para mostrarlas.
