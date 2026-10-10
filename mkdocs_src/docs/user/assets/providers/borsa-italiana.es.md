# 🇮🇹 Borsa Italiana

**Borsa Italiana** es la bolsa de Milán, gestionada por Euronext. Este proveedor lee precios, historial
de precios y detalles de instrumentos desde su sitio web público — no se necesita cuenta ni clave de API.

## 🔍 Qué ofrece

- **Precio actual**: el último precio de mercado. Para un fondo de inversión, su NAV — solo cuando está fechado
  hoy.
- **Historial**: apertura, máximo, mínimo, cierre y volumen diarios. Los fondos de inversión no tienen serie histórica: cada NAV
  se guarda en su propia fecha, así que el historial crece desde el día en que añades el fondo.
- **Búsqueda**: por nombre o ISIN. Cada instrumento aparece dos veces, 🇮🇹 y 🇬🇧: la bandera establece el
  idioma de su nombre y descripción. Los índices se omiten, ya que no se pueden comprar. ¿Sin resultados?
  LibreFolio también busca una página de Borsa Italiana coincidente en la web, a menos que tu administrador
  haya desactivado esto.
- **Detalles**: nombre, tipo, divisa, un sector y una descripción (mercado, emisor, vencimiento, cupón);
  el ticker para acciones; para fondos, el ISIN, las características del fondo y sus costes.

Cubre lo que cotiza Borsa Italiana — acciones italianas, ETFs y ETCs (ETFplus), bonos (MOT,
ExtraMOT, EuroTLX) y fondos de inversión cerrados (MIV) — además de fondos de inversión y SICAV.

## 💱 Divisa y tipo

- **Divisa** es aquella en la que Borsa Italiana cotiza los precios: EUR para ETFs y ETCs en ETFplus,
  incluso cuando el propio fondo está denominado en USD; USD para un bono negociado en dólares en EuroTLX. Si
  LibreFolio no puede leerla, deja tu divisa tal como está — compruébala antes de guardar.
- **Tipo**: los ETFs, ETCs y ETNs llegan todos como **ETF** simple. Si sabes qué contiene el fondo,
  refínalo (por ejemplo, **ETF de renta variable** o **ETF de materias primas**): una
  [comprobación posterior frente a los datos del proveedor](../create-edit.md#provider-data-comparison) mantiene tu elección.
- Los **bonos** obtienen el sector **Bonos gubernamentales** o **Bonos corporativos** (emisores supranacionales:
  **Financieros**) y, cuando se reconoce el emisor, su país — *Estados Unidos de América*
  se convierte en **USA**.

## ✏️ Configúralo

**Buscar en línea** completa todo. Para configurar el proveedor manualmente, abre el activo con
**Editar** (✏️) — o **+ Añadir activo** para uno nuevo — y despliega **Asignación de proveedor**:

1. Elige **Borsa Italiana** como **Proveedor**.
2. Escribe el **ISIN** del instrumento, por ejemplo `IT0003128367` (ENEL). Todas las páginas de instrumento en
   [borsaitaliana.it](https://www.borsaitaliana.it) lo muestran.
3. Elige el **Idioma**: 🇬🇧 Inglés o 🇮🇹 Italiano.
4. Haz clic en **Probar configuración** y luego guarda.

**Buscar en línea** también completa las otras tres opciones de configuración; configúralas manualmente solo en estos casos.

??? note "🧾 Código interno del fondo — para un fondo de inversión o SICAV"

    Los fondos de inversión se cotizan mediante el código de fondo propio de Borsa Italiana, no por el ISIN. Encuentra el fondo en
    [borsaitaliana.it](https://www.borsaitaliana.it/borsa/fondi/ricerca.html) y copia el código
    desde la dirección de su página: en `…/borsa/fondi/dettaglio/2FADB602822.html` el código es
    `2FADB602822`. Deja el campo vacío para cualquier otra cosa.

??? note "🧭 MIC de mercado y Plataforma — cuando la página del instrumento no se abre"

    Algunos mercados deben indicarse explícitamente. Abre el instrumento en borsaitaliana.it: el código después
    del ISIN en la dirección de la página es el **MIC de mercado** — en `…/scheda/US912810TU25-ETLX.html` es
    `ETLX`. **Plataforma** solo es necesaria en EuroTLX, donde es `TLX`.

    | Mercado | MIC de mercado | Plataforma |
    |--------|:---:|:---:|
    | MTA (acciones italianas) | `MTAA` | — |
    | MOT (bonos) | `MOTX` | — |
    | ExtraMOT (bonos) | `XMOT` | — |
    | ETFplus (ETFs, ETCs) | `ETFP` | — |
    | MIV (fondos de inversión cerrados) | `MIVX` | — |
    | EuroTLX (bonos) | `ETLX` | `TLX` |

    Por ejemplo, el bono del Tesoro de EE. UU. `US912810TU25` en EuroTLX funciona una vez que **MIC de mercado** es
    `ETLX` y **Plataforma** es `TLX`; sus precios están en USD.

## 🧾 Fondos de inversión y NAV

El NAV de un fondo se publica una vez al día, con retraso. LibreFolio guarda cada NAV en la fecha a la que
se refiere, nunca como el precio de hoy: hasta que llegue el siguiente, el fondo se valora al último
precio conocido — ese NAV, o tu propia operación si es más reciente.

El código del fondo se guarda en **Otros identificadores**; el ISIN real sigue siendo el identificador principal cuando
la página del fondo lo muestra.

## ⚠️ Límites

- LibreFolio espacia sus solicitudes al sitio web, por lo que sincronizar muchos activos de Borsa Italiana puede
  tardar unos minutos.
- Un mercado que LibreFolio aún no puede leer da un error que te pide que informes del ISIN en
  [GitHub](https://github.com/Librefolio/LibreFolio/issues).

## 🔗 Relacionado

- 📋 **[Resumen de activos](../index.md)** — Gestiona tu biblioteca de activos
- 🏦 **[Proveedores de activos](./index.md)** — Otras fuentes de datos
- 📡 **[justETF](./justetf.md)** — Fuente alternativa para datos de ETF
- 🛠️ **Para desarrolladores: [Proveedor de Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)** — Solicitudes, análisis de páginas y mapeo de campos
