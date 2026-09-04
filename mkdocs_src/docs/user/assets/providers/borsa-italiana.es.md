# 🇮🇹 Borsa Italiana

**Borsa Italiana** es la bolsa de valores italiana, operada por Euronext. LibreFolio incluye un **proveedor de datos de activos** dedicado que obtiene precios, series históricas y metadatos de instrumentos directamente desde el sitio web de Borsa Italiana.

---

## 🔍 Qué Proporciona

| Datos | Descripción |
|-------|-------------|
| **Precio actual** | Último precio oficial de mercado para instrumentos cotizados; NAV de fondos solo si está fechado hoy |
| **Precios históricos** | OHLCV diario para instrumentos cotizados; un punto NAV en la fecha real del NAV para fondos |
| **Metadatos del instrumento** | ISIN, segmento de mercado, divisa e identificadores alternativos cuando están disponibles |

Los activos negociados en Borsa Italiana incluyen acciones italianas (segmento MTA/MIL), ETF (ETFplus), bonos (MOT, ExtraMOT y EuroTLX), certificados (SeDeX), fondos cerrados (MIV) y fondos de inversión/SICAV.

!!! note "Sector y área geográfica para los bonos soberanos"

    Los bonos soberanos (BTP italianos, T-Bonds estadounidenses y otros emisores soberanos) se clasifican automáticamente: **sector = Financieros (100 %)**, y el país del emisor como área geográfica (p. ej. *Estados Unidos de América* → **USA**).

---

## ⚙️ Configuración

No se requiere clave de API ni registro: el proveedor extrae datos públicos del sitio web de Borsa Italiana. La configuración está disponible por activo en el panel **Provider Config** en la página de detalle del activo.

1. Navega hasta el activo que deseas rastrear.
2. Abre el panel **⚙️ Provider Config**.
3. Selecciona **Borsa Italiana** en la lista de proveedores.
4. Introduce el **ISIN** para instrumentos cotizados. Para fondos, usa la Búsqueda Inteligente para que LibreFolio pueda capturar automáticamente el código interno del fondo en Borsa.
5. Guarda — LibreFolio obtendrá la primera serie histórica en la siguiente sincronización.

!!! tip "Encontrar el ISIN"

    Puedes buscar el ISIN en [borsaitaliana.it](https://www.borsaitaliana.it) buscando el nombre del instrumento. El ISIN se muestra en cada página de detalle del instrumento.

!!! tip "La Búsqueda Inteligente puede usar enlaces de Borsa"

    Si la búsqueda normal no encuentra un fondo, pega o busca con la URL de la página del fondo/detalle de Borsa Italiana. La búsqueda inteligente de LibreFolio puede resolver las páginas Borsa compatibles, adjuntar los `provider_params` correctos y hacer que el fondo sea cotizable por su código interno.

### 🎛️ Parámetros del proveedor

Estos parámetros se configuran por ti al añadir el activo mediante la **Búsqueda Inteligente**. Para verlos o modificarlos a mano, abre el activo y despliega el panel **⚙️ Provider Config** — útil cuando la página de mercado de un instrumento no se resuelve, o para un activo guardado antes de que existieran estos parámetros.

| Campo | Clave | Cómo configurarlo |
|-------|-------|-------------------|
| **Language** (Idioma) | `language` | Elige `en` (English) o `it` (Italiano) en el menú — selecciona el idioma del nombre y los metadatos del activo descargados de Borsa Italiana. |
| **Fund internal code** (Código interno del fondo) | `codice_fondo` | **Solo fondos de inversión.** Abre la página del fondo en [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html), busca el fondo y lee el código en la URL de su página de detalle: `/borsa/fondi/dettaglio/<código>.html` → el código es la parte anterior a `.html` (p. ej. `2FADB602822`). Déjalo vacío para acciones, bonos y ETF. |
| **Market MIC** (MIC de mercado) | `mic` | El código del mercado en el que cotiza el instrumento. Encuéntralo abriendo la página del instrumento en borsaitaliana.it y mirando la URL: `…/scheda/<ISIN>-<MIC>.html` → el sufijo tras el ISIN es el MIC (p. ej. `US912810TU25-ETLX` → `ETLX`). Consulta la tabla siguiente para los valores comunes. |
| **Platform** (Plataforma) | `platform` | La plataforma de negociación. Solo algunos mercados la necesitan — EuroTLX exige `TLX`; déjala vacía para los demás. |

**Códigos de mercado comunes** — los valores a escribir al configurar un instrumento a mano:

| Mercado | `mic` | `platform` |
|---------|-------|------------|
| MTA (acciones italianas) | `MTAA` | — |
| MOT (bonos) | `MOTX` | — |
| ExtraMOT | `XMOT` | — |
| ETFplus | `ETFP` | — |
| EuroTLX | `ETLX` | `TLX` |
| SeDeX (certificados) | `SEDX` | — |
| MIV (fondos cerrados) | `MIVX` | — |

!!! example "Configurar a mano un bono EuroTLX"

    Un bono del Tesoro de EE. UU. cotizado en EuroTLX (p. ej. ISIN `US912810TU25`) no se resuelve desde la URL simple del ISIN. En borsaitaliana.it, la URL de su página termina en `…/obbligazioni/eurotlx/scheda/US912810TU25-ETLX.html`, así que su MIC es `ETLX`. En **⚙️ Provider Config** establece **Market MIC** en `ETLX` y **Platform** en `TLX`: el enlace a la página del instrumento, el precio actual y el historial funcionarán con normalidad. El historial de los bonos denominados en divisa extranjera puede expresarse en esa divisa (p. ej. USD).

---

## 🔄 Sincronización

El proveedor Borsa Italiana participa en el ciclo estándar de **sincronización de activos**. Actívalo manualmente desde la página de detalle del activo con el botón **🔄 Sync**, o deja que la tarea programada en segundo plano se ejecute por la noche.

!!! note "Límite de velocidad"

    El proveedor aplica una limitación automática para evitar ser bloqueado por Borsa Italiana. Si tienes muchos activos de este mercado, la sincronización completa puede tardar unos minutos.

!!! note "Fondos de inversión (NAV)"

    Los fondos de inversión y las SICAV se valoran según su **NAV** diario, publicado una vez al día con retraso. LibreFolio valora cada fondo por su código interno de Borsa, no por ISIN. El historial de precios muestra un punto NAV en su fecha real, y el valor actual se actualiza solo cuando el NAV publicado está fechado hoy (de lo contrario se utiliza tu último precio de compra como estimación).

!!! note "Identificadores alternativos"

    Algunos identificadores importados o descubiertos por el proveedor se almacenan como una lista editable de identificadores alternativos. Para los fondos de Borsa Italiana, esta lista puede incluir el código interno del fondo mientras que el ISIN real sigue siendo el identificador principal cuando está disponible.

---

## 🔗 Documentación para Desarrolladores

Para obtener detalles de implementación (formato de solicitudes, estrategia de extracción HTML, mapeo de campos), consulta:

→ [Manual para desarrolladores — Proveedor Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Relacionados

- 📋 **[Visión General de Activos](../index.md)** — Gestiona tu biblioteca de activos
- 🏦 **[Proveedores de Activos](./index.md)** — Otras fuentes de datos
- 📡 **[justETF](./justetf.md)** — Fuente alternativa para datos de ETF
