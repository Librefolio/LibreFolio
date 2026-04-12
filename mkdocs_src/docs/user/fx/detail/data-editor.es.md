# ✏️ Editor de Datos e Importación de CSV

El Editor de Datos le permite **ver, añadir, editar y eliminar** puntos de datos individuales de tipos de cambio. Para la carga masiva, incluye una herramienta integrada de **Importación de CSV**.

---

## 📝 Editor de Datos

Haga clic en el botón **Editar** (✏️) en la barra de herramientas del gráfico para abrir el panel del editor de datos:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="FX Data Editor" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👀 Visualización de Datos

El editor muestra una tabla desplazable con todos los puntos de datos para este par de divisas, ordenados por fecha (la más reciente primero):

- 📅 **Fecha** — La fecha de observación
- 💱 **Tipo de cambio** — El valor del tipo de cambio
- 🏛️ **Fuente** — De dónde provienen los datos (nombre del proveedor, importación de CSV o manual)

### ➕ Añadir un Punto de Datos

1. Haga clic en **"Añadir"** en la parte superior del editor
2. Seleccione la **fecha** en el selector de fecha
3. Introduzca el valor del **tipo de cambio**
4. Haga clic en **Guardar** — el punto se añade inmediatamente y el gráfico se actualiza

### ✏️ Editar un Punto de Datos

1. Haga clic en el **icono del lápiz** junto a cualquier fila
2. Modifique el valor del tipo de cambio
3. Haga clic en **Guardar** para confirmar

### 🗑️ Eliminar un Punto de Datos

1. Haga clic en el **icono de la papelera** junto a cualquier fila
2. Confirme la eliminación

!!! warning "Los datos sincronizados sobrescriben las ediciones manuales"

    Si edita o añade manualmente un punto de datos para una fecha que posteriormente sea cubierta por una sincronización, el valor del proveedor **sobrescribirá** su edición manual; el proveedor siempre se considera la fuente autorizada. Para pares donde desee un control manual total, utilice el proveedor MANUAL (sin fuente de datos automática); consulte [Provider Config](provider.md).

---

## 📥 Importación de CSV

Para la carga masiva de datos históricos de tipos de cambio, utilice la herramienta de Importación de CSV.

### 🔓 Cómo Acceder

1. Abra el Editor de Datos (icono del lápiz ✏️)
2. Haga clic en **"Import CSV"** para abrir el modal de importación

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="CSV Import Modal" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

### 📄 Formato del Archivo CSV

El archivo CSV debe tener **exactamente 2 columnas** con una **fila de encabezado** que especifique la dirección:

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
2024-01-04;1.0911
```

### 📏 Reglas

| Regla | Detalles |
|------|---------|
| **Separador** | Punto y coma (`;`) |
| **Formato de fecha** | `YYYY-MM-DD` |
| **Valores de tipo de cambio** | Números decimales positivos |
| **Encabezado** | Obligatorio — debe contener la dirección (ej., `EUR>USD`) |
| **Flecha de dirección** | Use `>` o `<` (ambos son compatibles) |

### ↔️ Dirección en el Encabezado

El encabezado indica a LibreFolio en qué dirección se expresan los tipos de cambio:

- ➡️ `date;EUR>USD` significa: **1 EUR = X USD** (los tipos de cambio son EUR→USD)
- ⬅️ `date;USD>EUR` significa: **1 USD = X EUR** (los tipos de cambio son USD→EUR)

Si está en la página de EUR/USD y su CSV tiene tipos de cambio `USD>EUR`, LibreFolio invertirá automáticamente los valores.

---

### 🔀 Dirección e Intercambio

El modal de importación muestra una **barra de dirección** que indica cómo se interpretarán sus datos:

- ➡️ **Divisa izquierda** → **Divisa derecha**: el tipo de cambio indica cuánta divisa de la derecha obtiene por 1 unidad de la divisa de la izquierda
- 🔄 Use el **botón de intercambio (⇄)** para invertir la dirección si sus datos están en el formato opuesto

El encabezado en su CSV determina la dirección automáticamente. Si el encabezado dice `EUR>USD`, el modal establece la dirección a EUR→USD.

---

### 📋 Ejemplos

#### ✅ Archivo Válido Mínimo

```csv
date;EUR>USD
2024-01-02;1.1045
2024-01-03;1.0982
```

#### ✅ Dirección Invertida

```csv
date;USD>EUR
2024-01-02;0.9053
2024-01-03;0.9106
```

Esto es equivalente al primer ejemplo: LibreFolio invierte `0.9053` a `1/0.9053 ≈ 1.1045`.

#### ❌ Archivo Inválido

```csv
date;GBP>JPY
2024-01-02;188.45
```

Esto fallará si está en la página de EUR/USD; las divisas del encabezado deben coincidir con el par de la página.

---

### ⚠️ Errores Comunes

| Error | Causa | Solución |
|-------|-------|-----|
| **"Header currencies don't match"** | El encabezado tiene divisas que no están en esta página | Verifique el par y corrija el encabezado |
| **"Missing or invalid header"** | No hay fila de encabezado o el formato es incorrecto | Añada un encabezado como `date;EUR>USD` |
| **"Duplicate dates"** | La misma fecha aparece varias veces | Elimine los duplicados |
| **"Invalid rate"** | Valor no numérico o negativo | Asegúrese de que todos los tipos de cambio sean números positivos |
| **"Invalid date format"** | La fecha no está en formato `YYYY-MM-DD` | Corrija el formato de la fecha |

---

### 🔀 Comportamiento de Fusión (Merge)

Al importar vía CSV o añadir puntos manualmente en el editor:

- Los cambios se aplican primero al **caché local del cliente** (visibles inmediatamente en el gráfico)
- Los cambios **no se persisten** en la base de datos hasta que haga clic en **Guardar**
- 🔄 Los **puntos de datos existentes** en la base de datos serán **sobrescritos** con los valores importados al guardar
- 🆕 Se añaden **nuevas fechas**
- ✅ Las **fechas que no están en la importación** permanecen intactas

Esto le permite actualizar selectivamente rangos de fechas específicos sin afectar el resto de sus datos.

!!! tip "Ideal para pares MANUAL"

    El editor de datos es más útil para pares configurados con el proveedor MANUAL (sin fuente de datos automática). Para pares respaldados por un proveedor, las ediciones manuales serán sobrescritas en la siguiente sincronización.
