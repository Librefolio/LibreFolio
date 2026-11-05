# 🇮🇹 Borsa Italiana

**Borsa Italiana** es la bolsa de Milán, gestionada por Euronext. Este proveedor lee los precios, el historial de precios y los detalles de los instrumentos desde su sitio web público — no se necesita cuenta ni clave de API.

## 🔍 Qué ofrece

- **Precio actual**: el último precio de mercado. Para un fondo de inversión, su NAV — solo cuando tiene fecha de hoy.
- **Historial**: apertura, máximo, mínimo, cierre y volumen diarios. Los fondos de inversión no tienen series pasadas: cada NAV se guarda en su propia fecha, así que el historial crece desde el día en que añades el fondo.
- **Búsqueda**: por nombre o ISIN. Cada instrumento aparece dos veces, 🇮🇹 y 🇬🇧 — o solo en tu [idioma preferido](#preferred-language): la bandera establece el idioma de su nombre y descripción. Los índices se omiten, ya que no puedes comprarlos. ¿Ningún resultado?
  LibreFolio también busca en la web una página de Borsa Italiana que coincida, a menos que tu administrador lo haya desactivado.
- **Detalles**: nombre, tipo, divisa, un sector y una descripción (mercado, emisor, vencimiento, cupón); el ticker para acciones; para fondos, el ISIN, las características del fondo y sus costes.

Cubre lo que Borsa Italiana cotiza — acciones italianas, ETFs y ETCs (ETFplus), bonos (MOT, ExtraMOT, EuroTLX) y fondos de inversión cerrados (MIV) — además de fondos de inversión y SICAVs.

## 💱 Divisa y tipo

- La **divisa** es aquella en la que Borsa Italiana cotiza los precios: EUR para ETFs y ETCs en ETFplus, incluso cuando el fondo en sí está denominado en USD; USD para un bono negociado en dólares en EuroTLX. Si LibreFolio no puede leerla, deja tu divisa tal como está — compruébala antes de guardar.
- **Tipo**: los ETFs, ETCs y ETNs llegan todos como **ETF** simple. Si sabes qué contiene el fondo, refínalo (por ejemplo, **Equity ETF** o **Commodity ETF**): una [comprobación posterior con los datos del proveedor](../create-edit.md#provider-data-comparison) mantiene tu elección.
- **Bonos**: reciben el sector **Government Bonds** o **Corporate Bonds** (emisores supranacionales: **Financials**) y, cuando se reconoce al emisor, su país — *United States of America* pasa a ser **USA**.

## ✏️ Configúralo

**Buscar en línea** rellena todo. Para configurar el proveedor a mano, abre el activo con **Editar** (✏️) — o **+ Añadir activo** para uno nuevo — y despliega **Asignación de proveedor**:

1. Elige **Borsa Italiana** como **Proveedor**.
2. Escribe el **ISIN** del instrumento, por ejemplo `IT0003128367` (ENEL). La página de cada instrumento en [borsaitaliana.it](https://www.borsaitaliana.it) lo muestra.
3. Elige el **Idioma**: 🇬🇧 Inglés o 🇮🇹 Italiano.
4. Haz clic en **Probar configuración** y luego guarda.

**Buscar en línea** también rellena los otros tres parámetros de configuración; configúralos a mano solo en estos casos.

??? note "🧾 Código interno del fondo — para un fondo de inversión o una SICAV"

    Los fondos de inversión se valoran con el código de fondo propio de Borsa Italiana, no con el ISIN. Encuentra el fondo en [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html) y copia el código de la dirección de su página: en `…/borsa/fondi/dettaglio/2FADB602822.html` el código es `2FADB602822`. Deja el campo vacío para cualquier otra cosa.

??? note "🧭 MIC de mercado y plataforma — cuando la página del instrumento no se abre"

    Algunos mercados deben indicarse explícitamente. Abre el instrumento en borsaitaliana.it: el código que sigue al ISIN en la dirección de la página es el **MIC de mercado** — en `…/scheda/US912810TU25-ETLX.html` es `ETLX`. **Plataforma** solo se necesita en EuroTLX, donde es `TLX`.

    | Mercado | MIC de mercado | Plataforma |
    |--------|:---:|:---:|
    | MTA (acciones italianas) | `MTAA` | — |
    | MOT (bonos) | `MOTX` | — |
    | ExtraMOT (bonos) | `XMOT` | — |
    | ETFplus (ETFs, ETCs) | `ETFP` | — |
    | MIV (fondos de inversión cerrados) | `MIVX` | — |
    | EuroTLX (bonos) | `ETLX` | `TLX` |

    Por ejemplo, el bono del Tesoro estadounidense `US912810TU25` en EuroTLX funciona una vez que **MIC de mercado** es `ETLX` y **Plataforma** es `TLX`; sus precios están en USD.

### 🌐 Tu idioma preferido {: #preferred-language }

¿Eliges siempre el mismo idioma en la búsqueda? Elígelo una vez como **Idioma preferido**, en **Borsa Italiana** dentro de **Configuración › Plugins**, o con **Configurar** junto al proveedor en el diálogo del activo. Tus búsquedas mostrarán entonces cada instrumento una sola vez, 🇮🇹 italiano o 🇬🇧 inglés. **Ambos idiomas**, el valor predeterminado, muestra ambos, italiano primero. El sitio web se busca de la misma manera elijas lo que elijas.

Es una configuración personal: solo cambia tus propias búsquedas, nunca un precio ni un activo que ya tengas, y el **Idioma** de un activo que configures a mano sigue siendo elección tuya. Consulta [Configuración de plugins](../../settings/plugins.md#search-preferences).

## 🧾 Fondos de inversión y NAV

El NAV de un fondo se publica una vez al día, con retraso. LibreFolio guarda cada NAV en la fecha a la que se refiere, nunca como el precio de hoy: hasta que llegue el siguiente, el fondo se valora al último precio conocido — ese NAV, o tu propia operación si es más reciente.

El código del fondo se guarda en **Otros identificadores**; el ISIN real sigue siendo el identificador principal cuando la página del fondo lo muestra.

## ⚠️ Límites

- LibreFolio espacia sus solicitudes al sitio web, por lo que sincronizar muchos activos de Borsa Italiana puede tardar unos minutos.
- Un mercado que LibreFolio aún no puede leer devuelve un error que te pide informar del ISIN en [GitHub](https://github.com/Librefolio/LibreFolio/issues).

## 🔗 Relacionado

- 📋 **[Resumen de activos](../index.md)** — Gestiona tu biblioteca de activos
- 🏦 **[Proveedores de activos](./index.md)** — Otras fuentes de datos
- 📡 **[justETF](./justetf.md)** — Fuente alternativa para datos de ETFs
- 🧩 **[Configuración de plugins](../../settings/plugins.md)** — Tu idioma preferido en la búsqueda
- 🛠️ **Para desarrolladores: [Proveedor de Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)** — Solicitudes, análisis de páginas y mapeo de campos
