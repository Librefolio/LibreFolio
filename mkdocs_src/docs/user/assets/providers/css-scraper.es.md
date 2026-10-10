# <img src="../../../../static/cssscraper.png" alt=""> CSS Scraper

El CSS Scraper lee el precio de un activo desde cualquier página web pública, usando un selector CSS que apunta
al número. Úsalo cuando ningún otro proveedor cubra el instrumento. En la lista **Proveedor** se llama
**CSS Web Scraper**.

## 🔍 Qué ofrece

- ✅ **Precio actual**: se lee de la página en cada sincronización, en la divisa que elijas.
- ❌ **Historial**: no hay. Cada sincronización guarda el precio del día, así que el historial crece desde el día en que
  empiezas.
- ❌ **Búsqueda** y **detalles**: no hay — tú mismo introduces la dirección de la página y la configuración.

## 🧩 Configúralo

### 1️⃣ Copia el selector CSS del precio

El selector indica a LibreFolio qué elemento de la página contiene el precio.

=== "Chrome"

    1. Abre la página y haz clic derecho sobre el precio.
    2. Elige **Inspeccionar** (o pulsa `F12`): DevTools resalta el elemento del precio.
    3. Haz clic derecho sobre el elemento resaltado y luego **Copiar** → **Copiar selector**.

=== "Firefox"

    1. Abre la página y haz clic derecho sobre el precio.
    2. Elige **Inspeccionar** (o pulsa `F12`): el Inspector resalta el elemento del precio.
    3. Haz clic derecho sobre el elemento resaltado y luego **Copiar** → **Selector CSS**.

### 2️⃣ Rellena la configuración del proveedor

En **Asignación de proveedor**, elige **CSS Web Scraper** y pega la dirección de la página en **URL**. La
configuración aparece con sus nombres técnicos:

| Configuración | Obligatorio | Qué introducir |
|---|:---:|---|
| `current_css_selector` | ✅ | El selector que copiaste, p. ej. `.summary-value strong` |
| `currency` | ✅ | La divisa del precio, p. ej. `EUR` |
| `decimal_format` | — | `us` para `1,234.56` (el valor predeterminado) o `eu` para `1.234,56` |
| `timeout` | — | Segundos de espera para la página (predeterminado `30`) |
| `user_agent` | — | Cómo se presenta LibreFolio ante el sitio (predeterminado `LibreFolio/1.0`) |

### 3️⃣ Pruébalo

Haz clic en **Probar configuración**: **Precio actual** debe mostrar el número que ves en la página. Se espera el ⚠️ en
**Historial**, ya que este proveedor no tiene ninguno.

!!! example "Un BTP en Borsa Italiana"

    - **URL**: `https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/IT0005634800.html?lang=en`
    - `current_css_selector`: `.summary-value strong`
    - `currency`: `EUR`
    - `decimal_format`: `us` — la página en inglés muestra `100.39`. La página en italiano (`lang=it`)
      muestra `100,39`, así que ahí usa `eu`.

    Para instrumentos cotizados en Borsa Italiana, el proveedor [Borsa Italiana](borsa-italiana.md)
    también aporta su historial.

## 🛠️ Solución de problemas

| Qué ves | Qué hacer |
|---|---|
| **No se encontró el elemento del precio** | Puede que el diseño de la página haya cambiado: vuelve a copiar el selector. |
| **No se pudo interpretar el precio** | Comprueba `decimal_format`. El elemento debe contener solo el número: los espacios, €, $, £, ¥ y % se ignoran; las letras como `EUR`, no. |
| **Error HTTP** o **Solicitud fallida** | Comprueba la URL; aumenta `timeout` para un sitio lento. El error 403 significa que el sitio rechaza las visitas automatizadas. |
| Un número incorrecto | El selector coincide con otro elemento (LibreFolio usa la primera coincidencia): hazlo más específico. |

## ⚠️ Límites

- LibreFolio lee la página tal como la envía el sitio, sin ejecutar sus scripts: un precio rellenado
  por JavaScript no se puede leer, ni tampoco las páginas detrás de un inicio de sesión.
- Cuando el sitio cambie su diseño, puede que el selector deje de coincidir: vuelve a probar y copia uno nuevo.

## 🔗 Relacionado

- ✏️ **[Editor de datos](../detail/data-editor.md)** — Introduce o corrige precios a mano
- 🛠️ **Para desarrolladores: [Proveedor CSS Scraper](../../../developer/backend/assets/provider_cssscraper.md)** — Solicitud, análisis y códigos de error
