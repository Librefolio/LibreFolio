# 🇮🇹 Borsa Italiana

**Borsa Italiana** es la bolsa de valores italiana, operada por Euronext. LibreFolio incluye un **proveedor de datos de activos** dedicado que obtiene precios, series históricas y metadatos de instrumentos directamente desde el sitio web de Borsa Italiana.

---

## 🔍 Qué Proporciona

| Datos | Descripción |
|-------|-------------|
| **Precio actual** | Último precio oficial de mercado para instrumentos cotizados; NAV de fondos solo si está fechado hoy |
| **Precios históricos** | OHLCV diario para instrumentos cotizados; un punto NAV en la fecha real del NAV para fondos |
| **Metadatos del instrumento** | ISIN, segmento de mercado, divisa e identificadores alternativos cuando están disponibles |

Los activos negociados en Borsa Italiana incluyen acciones italianas (segmento MTA/MIL), ETF (ETFplus), bonos (MOT) y fondos de inversión/SICAV.

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
