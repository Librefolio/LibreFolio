# ✏️ Editor de Datos e Importación CSV

El Editor de Datos te permite **ver, agregar, editar y eliminar** puntos de datos individuales de tipos de cambio. Para carga masiva, incluye una herramienta integrada de **Importación CSV**.

---

## 📝 Editor de Datos

Haz clic en el botón **Editar** (✏️) en la barra de herramientas del gráfico para abrir el panel del editor de datos:

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-editor" alt="Editor de Datos FX" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

### 👀 Visualización de Datos

El editor muestra una tabla desplazable con todos los puntos de datos de este par de divisas, ordenados por fecha (más reciente primero):

- 📅 **Fecha** — La fecha de observación
- 💱 **Tipo** — El valor del tipo de cambio
- 🏛️ **Fuente** — De dónde provienen los datos (nombre del proveedor, importación CSV o manual)

### ➕ Agregar un Punto de Datos

1. Haz clic en **"Agregar"** en la parte superior del editor
2. Selecciona la **fecha** desde el selector de fecha
3. Ingresa el valor del **tipo**
4. Haz clic en **Guardar** — el punto se agrega inmediatamente y el gráfico se actualiza

### ✏️ Editar un Punto de Datos

1. Haz clic en el **icono de lápiz** junto a cualquier fila
2. Modifica el valor del tipo
3. Haz clic en **Guardar** para confirmar

### 🗑️ Eliminar un Punto de Datos

1. Haz clic en el **icono de basura** junto a cualquier fila
2. Confirma la eliminación

!!! warning "Las ediciones manuales sobrescriben los datos sincronizados"
 Si editas o agregas manualmente un punto de datos para una fecha que fue sincronizada desde un proveedor, tu valor manual tiene precedencia. La próxima sincronización no sobrescribirá las entradas manuales.

---

## 📥 Importación CSV

Para carga masiva de datos históricos de tipos de cambio, usa la herramienta de Importación CSV.

### 🔓 Cómo Acceder

1. Abre el Editor de Datos (icono de lápiz ✏️)
2. Haz clic en **"Importar CSV"** para abrir el modal de importación

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="detail-csv-import" alt="Modal de Importación CSV" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
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
|-------|----------|
| **Separador** | Punto y coma (`;`) |
| **Formato de fecha** | `AAAA-MM-DD` |
| **Valores del tipo de cambio** | Números decimales positivos |
| **Encabezado** | Requerido — debe tener dos columnas: la primera llamada 'date' y la segunda con la dirección (ej., `date;EUR>USD`) |
| **Flecha de dirección** | Usa `>` o `<` (ambas son compatibles) |

### ↔️ Dirección en el Encabezado

El encabezado le indica a LibreFolio en qué dirección se expresan los tipos:

- ➡️ `date;EUR>USD` significa: **1 EUR = X USD** (los tipos son EUR→USD)
- ⬅️ `date;USD>EUR` significa: **1 USD = X EUR** (los tipos son USD→EUR)

Si estás en la página EUR/USD y tu CSV tiene tipos `USD>EUR`, LibreFolio invertirá automáticamente los valores.

---

### 🔀 Dirección e Intercambio

El modal de importación muestra una **barra de dirección** que indica cómo se interpretarán tus datos:

- ➡️ **Divisa izquierda** → **Divisa derecha**: el tipo indica cuánto de la divisa derecha obtienes por 1 unidad de la divisa izquierda
- 🔄 Usa el **botón de intercambio (⇄)** para invertir la dirección si tus datos están en el formato opuesto

El encabezado en tu CSV determina la dirección automáticamente. Si el encabezado dice `EUR>USD`, el modal establece la dirección a EUR→USD.

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

Esto es equivalente al primer ejemplo — LibreFolio calcula el inverso (1/0.9053 ≈ 1.1045) para convertir a la dirección EUR→USD.

#### ❌ Archivo Inválido

```csv
date;GBP>JPY
2024-01-02;188.45
```

Esto fallará si estás en la página EUR/USD — las monedas del encabezado deben coincidir con el par de la página.

---

### ⚠️ Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| **"Las monedas del encabezado no coinciden"** | El encabezado tiene monedas que no están en esta página | Verifica el par y corrige el encabezado |
| **"Encabezado faltante o inválido"** | No hay fila de encabezado, o formato incorrecto | Agrega un encabezado como `date;EUR>USD` |
| **"Fechas duplicadas"** | La misma fecha aparece múltiples veces | Elimina duplicados |
| **"Valor inválido"** | No numérico o negativo | Asegúrate de que todos los tipos sean números positivos |
| **"Formato de fecha inválido"** | Fecha no en formato `AAAA-MM-DD` | Corrige el formato de fecha |

---

### 🔀 Comportamiento en la Fusión

Al importar, si una fecha ya existe en la base de datos:

- 🔄 **Los puntos de datos existentes se sobrescriben** con los valores importados
- 🆕 **Las fechas nuevas** se agregan
- ✅ **Las fechas que no están en el CSV** se dejan sin cambios

Esto te permite actualizar selectivamente rangos de fechas específicos sin afectar el resto de tus datos.
