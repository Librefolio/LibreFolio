# ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" } Interés (Transacción)

Una **transacción de interés** registra los ingresos por interés recibidos de bonos, cuentas de ahorro, préstamos P2P u otros instrumentos de renta fija. Representa el impacto a nivel de cartera de un [evento de interés](../asset-events/interest.md).

---

## 🔑 Propiedades Clave

| Propiedad | Detalle |
|----------|--------|
| **Código** | `INTEREST` |
| **Efecto en efectivo** | ⬆️ Aumenta el saldo |
| **Efecto en activo** | — (principal sin cambios) |
| **Evento fiscal** | Sí (ingresos imponibles) |

---

## 📊 Fuentes de Interés

| Fuente | Descripción | Frecuencia |
|--------|-------------|-----------|
| **Cupones de bonos** | Pagos de tasa fija o flotante | Semestral / Anual |
| **Intereses de ahorro** | Intereses sobre depósitos en efectivo | Mensual / Trimestral |
| **Pagos de préstamos P2P** | Componente de intereses de los reembolsos del préstamo | Mensual |
| **Rendimientos de Crowdfunding** | Rendimientos de tasa fija en proyectos | Varía |

---

## 💡 Cuándo usarlo

Utilice una transacción `INTEREST` cuando el efectivo llegue a su cuenta de bróker como ingresos por interés. Esto es distinto de:

- **Dividendo** — ingresos por renta variable (acciones, ETF de distribución)
- **Liquidación al Vencimiento** — devolución del principal al vencimiento del bono

!!! tip "Theory & formulas"

    Para las matemáticas del devengo de intereses (simple vs compuesto, convenciones de conteo de días, métricas de rendimiento), consulte:

    - **[📈 Eventos de Interés](../asset-events/interest.md)** — Mecánica de devengo e impacto en el precio
    - **[📅 Convenciones de Conteo de Días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de interés

---

## 🔗 Relacionado

- 📈 **[Eventos de Interés](../asset-events/interest.md)** — Mecánica de devengo y cupones
- 🏛️ **[Bonos](../asset-types/bonds.md)** — El activo principal que genera intereses
- 📈 **[Retornos y Tasas de Crecimiento](../../fundamentals/returns.md)** — Medición del rendimiento de los ingresos
- 📅 **[Convenciones de Conteo de Días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de interés
