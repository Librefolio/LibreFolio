# 🔍 Proveedor CSS Scraper

El proveedor CSS Scraper le permite extraer datos de precios de cualquier página web utilizando selectores CSS. Esto es particularmente útil para instrumentos que no están cubiertos por otros proveedores, como los bonos del gobierno italiano (BTP) en Borsa Italiana.

## 📊 Capacidades

- ✅ **Precio Actual**: Extrae el precio de una página web
- ❌ **Historial**: No compatible (⚠️ advertencia, no es un error)
- ❌ **Búsqueda**: No compatible

## 🔧 Configuración

- **Identificador**: La URL completa de la página de la cual extraer datos
- **Tipo de Identificador**: `OTHER`
- **Parámetros**:

| Parámetro | Requerido | Descripción | Ejemplo |
|-----------|:---:|---|---|
| `current_css_selector` | ✅ | Selector CSS para el elemento del precio | `.summary-value strong` |
| `currency` | ✅ | Código de moneda ISO 4217 | `EUR` |
| `decimal_format` | ❌ | `us` (1,234.56) o `eu` (1.234,56) | `eu` |
| `timeout` | ❌ | Tiempo de espera HTTP en segundos (predeterminado: 30) | `30` |
| `user_agent` | ❌ | Encabezado User-Agent personalizado | `LibreFolio/1.0` |

## 🔎 Cómo encontrar el selector CSS

### Paso a paso (Chrome)

1. Abra la página con el precio en Chrome
2. Haga **clic derecho** sobre el valor del precio
3. Seleccione **Inspeccionar** (o presione `F12`)
4. En el panel Elements de las DevTools, el elemento del precio estará resaltado
5. Haga **clic derecho** en el elemento resaltado en las DevTools
6. Seleccione **Copiar** → **Copiar selector**
7. Péguelo en el campo `current_css_selector`

### Paso a paso (Firefox)

1. Abra la página con el precio en Firefox
2. Haga **clic derecho** sobre el valor del precio
3. Seleccione **Inspeccionar elemento** (o presione `F12`)
4. En el Inspector, haga **clic derecho** en el elemento resaltado
5. Seleccione **Copiar** → **Selector CSS**
6. Péguelo en el campo `current_css_selector`

### 💡 Ejemplo: Borsa Italiana BTP

Para un BTP en Borsa Italiana (por ejemplo, `IT0005634800`):

**URL** (versión en inglés):
```
https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en
```

**Selector CSS**:
```
.summary-value strong
```

**Configuración**:
- Identificador: `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
- `current_css_selector`: `.summary-value strong`
- `currency`: `EUR`
- `decimal_format`: `us` (la página en inglés usa el formato US: 100.39)

Para la versión italiana, utilice `decimal_format`: `eu` (la página italiana usa el formato EU: 100,39).

## 🔢 Formato Decimal

| Formato | Ejemplo | Cuándo usarlo |
|--------|---------|-------------|
| `us` | 1,234.56 | Páginas en inglés/EE. UU. (punto como separador decimal) |
| `eu` | 1.234,56 | Páginas italianas/alemanas/francesas (coma como separador decimal) |

## 🛠️ Solución de problemas

### "Selector not found"
El selector CSS no coincide con ningún elemento de la página. Es posible que la estructura de la página haya cambiado; vuelva a inspeccionar y copie un nuevo selector.

### "Connection timeout"
La página tardó demasiado en responder. Intente aumentar el parámetro `timeout` o verifique si la URL es correcta.

### "Parse error"
No se pudo interpretar el texto del precio como un número. Verifique la configuración de `decimal_format`: si la página muestra `100,39`, use `eu`; si muestra `100.39`, use `us`.

### El precio muestra 0 o un valor incorrecto
Es posible que el selector esté coincidiendo con un elemento diferente. Intente usar un selector más específico. Use las DevTools para verificar exactamente con qué elemento coincide su selector.
