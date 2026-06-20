# <img src="https://www.borsaitaliana.it/media-rwd/assets/images/favicon.ico" alt=""> Borsa Italiana

**Borsa Italiana** es la bolsa de valores italiana, operada por Euronext. LibreFolio incluye un **proveedor de activo** dedicado que obtiene precios, series históricas y metadatos de instrumentos directamente desde el sitio web de Borsa Italiana.

---

## 🔍 Qué Proporciona

| Datos | Descripción |
|------|-------------|
| **Precio actual** | Último precio oficial de mercado |
| **OHLCV Histórico** | Series diarias de apertura/máximo/mínimo/cierre/volumen |
| **Metadatos del instrumento** | ISIN, segmento de mercado, moneda |

Los activos negociados en Borsa Italiana incluyen acciones italianas (segmento MTA/MIL), ETFs (ETFplus), bonos (MOT) y fondos.

---

## ⚙️ Configuración

No se requiere clave de API ni registro; el proveedor extrae datos públicos del sitio web de Borsa Italiana. La configuración está disponible por activo en el panel **Provider Config** de la página de detalles del activo.

1. Navegue hasta el activo que desea rastrear.
2. Abra el panel **⚙️ Provider Config**.
3. Seleccione **Borsa Italiana** de la lista de proveedores.
4. Ingrese el **ISIN** o el código de ticker de Borsa Italiana.
5. Guarde — LibreFolio obtendrá la primera serie histórica en la siguiente sincronización.

!!! tip "Búsqueda del ISIN"

    Puede buscar el ISIN en [borsaitaliana.it](https://www.borsaitaliana.it) buscando el nombre del instrumento. El ISIN se muestra en cada página de detalles del instrumento.

---

## 🔄 Sincronización

El proveedor de Borsa Italiana participa en el ciclo estándar de **asset sync**. Actívelo manualmente desde la página de detalles del activo con el botón **🔄 Sync**, o deje que la tarea programada en segundo plano se ejecute durante la noche.

!!! note "Rate limiting"

    El proveedor aplica un control de flujo automático para evitar ser bloqueado por Borsa Italiana. Si tiene muchos activos de esta bolsa, la sincronización completa puede tardar unos minutos.

---

## 🔗 Documentación para Desarrolladores

Para detalles de implementación (formato de solicitud, estrategia de análisis de HTML, mapeo de campos), consulte:

→ [Manual del Desarrollador — Proveedor de Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Relacionados

- 📋 **[Descripción general de activos](../index.md)** — Gestione su biblioteca de activos
- 🏦 **[Proveedores de activos](./index.md)** — Otras fuentes de datos
- 📡 **[justETF](./justetf.md)** — Fuente alternativa para datos de ETF
