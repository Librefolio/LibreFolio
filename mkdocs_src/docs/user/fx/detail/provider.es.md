# 🔌 Configuración de Proveedores

Cada par de divisas en LibreFolio está respaldado por uno o más **proveedores de datos**: bancos centrales que suministran los datos de tipos de cambio. La Configuración de Proveedores le permite ver y modificar qué proveedores se utilizan para un par específico.

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="fx" data-name="provider-config" alt="Configuración de Proveedores" style="width: 100%; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.1);">
</div>

---

## 🔓 Cómo Acceder

Haga clic en el botón de **Proveedor** (⚙️) en la barra de herramientas del gráfico en la página de Detalle del Par. Esto abrirá el modal de configuración de proveedores que muestra la configuración de ruta actual.

---

## 📋 Contenido del modal

El modal muestra:

- 🛤️ **Ruta(s) Actual(es)** — La(s) fuente(s) de datos activa(s) para este par, en orden de prioridad
- 🔀 **Tipo de Ruta** — Si se trata de una ruta **Directa** (proveedor único) o una ruta de **Cadena** (saltos múltiples a través de una divisa intermedia)
- 🏛️ **Detalles del Proveedor** — Nombre, icono y divisa base de cada proveedor en la ruta

---

## 🔧 Cambiar Proveedores

Puede configurar **uno o más** proveedores de datos para cada par. Múltiples proveedores actúan como una **cadena de fallback**: si la fuente primaria falla, el sistema intenta automáticamente la siguiente.

Para cambiar o añadir proveedores:

1. Abra el modal de Configuración de Proveedores
2. **Elimine** la ruta actual si es necesario
3. **Añada una nueva ruta** — el sistema descubrirá las rutas disponibles (al igual que al [añadir un nuevo par](../add-pair.md))
4. **Reordene** las rutas para establecer prioridades (arrastre y suelte o use los botones de flecha)
5. Haga clic en **Guardar** — la siguiente sincronización obtendrá los datos del proveedor disponible con mayor prioridad

---

## 🔢 Prioridad y Fallback

Cuando se configuran múltiples rutas para un par:

- Las rutas se prueban **en orden de prioridad** (superior = prioridad más alta)
- Si el proveedor primario falla (tiempo de espera agotado, error de API), el sistema hace fallback automáticamente a la siguiente ruta
- Puede **reordenar** las rutas para cambiar las prioridades

!!! example "Ejemplo de Fallback"

    EUR/USD configurado con:

    1. **ECB** (primario) — Banco Central Europeo
    2. **FED** (fallback) — Reserva Federal

    Si la API del ECB no está disponible durante la sincronización, el sistema utilizará automáticamente la FED en su lugar.

---

## 📚 Relacionados

- ➕ **[Añadir un Par](../add-pair.md)** — Descubrimiento completo de rutas (rutas directas + de cadena)
- 🔄 **[Sincronización](../sync.md)** — Cómo utiliza la sincronización los proveedores configurados
- 📋 **[Lista de Proveedores FX](../../../developer/backend/fx/providers_list.md)** — Detalles técnicos de cada proveedor (ECB, FED, BOE, SNB)

!!! tip "🔗 Cómo se calculan las rutas en cadena"

    Para conocer el algoritmo matemático detrás de las cadenas de conversión de saltos múltiples, consulte [FX Chain Algorithm](../../../developer/frontend/fx-chain-algorithm.md).
