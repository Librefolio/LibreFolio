# 🇮🇹 Borsa Italiana

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

No se requiere clave API ni registro; el proveedor actúa como un scraper de datos públicos del sitio web de Borsa Italiana. La configuración está disponible por activo en el panel **Provider Config** de la página de detalles del activo.

1. Navegue al activo que desea rastrear.
2. Abra el panel **⚙️ Provider Config**.
3. Seleccione **Borsa Italiana** en la lista de proveedores.
4. Ingrese el **ISIN** o el código ticker de Borsa Italiana.
5. Guardar — LibreFolio obtendrá la primera serie histórica en la próxima sincronización.

!!! tip "Cómo encontrar el ISIN"

    Puede buscar el ISIN en [borsaitaliana.it](https://www.borsaitaliana.it) buscando el nombre del instrumento. El ISIN se muestra en cada página de detalles del instrumento.

---

## 🔄 Sincronización

El proveedor de Borsa Italiana participa en el ciclo estándar de **sincronización de activos**. Actívelo manualmente desde la página de detalles del activo con el botón **🔄 Sync**, o permita que la tarea programada en segundo plano se ejecute durante la noche.

!!! note "Limitación de tasa (Rate limiting)"

    El proveedor aplica una limitación automática para evitar ser bloqueado por Borsa Italiana. Si tiene muchos activos de esta bolsa, la sincronización completa puede tardar unos minutos.

---

## 🔗 Documentación para Desarrolladores

Para detalles de implementación (formato de solicitud, estrategia de análisis HTML, mapeo de campos), consulte:

→ [Manual del Desarrollador — Proveedor de Borsa Italiana](../../../developer/backend/assets/provider_borsa_italiana.md)

---

## 🔗 Relacionado

- 📋 **[Descripción General de Activos](../index.md)** — Gestione su biblioteca de activos
- 🏦 **[Proveedores de Activos](./index.md)** — Otras fuentes de datos
- 📡 **[justETF](./justetf.md)** — Fuente alternativa para datos de ETF
