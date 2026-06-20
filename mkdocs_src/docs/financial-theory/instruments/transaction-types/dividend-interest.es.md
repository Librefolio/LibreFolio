# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividendos e Intereses ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-dividend" alt="Formulario de Transacción — DIVIDENDOS">
</div>

Los **dividendos** y los **intereses** representan el rendimiento generado por los activos de su cartera. Son pagos en efectivo recibidos sin vender el activo subyacente.

---

## 🔑 Propiedades Clave

| Propiedad | Dividendo | Interés |
|----------|----------|----------|
| **Código** | `DIVIDEND` | `INTEREST` |
| **Efecto en caja** | ⬆️ Aumenta el saldo | ⬆️ Aumenta el saldo |
| **Efecto en el activo** | — (cantidad sin cambios) | — (principal sin cambios) |
| **Evento fiscal** | Sí (ingreso imponible) | Sí (ingreso imponible) |

---

## 💡 Cuándo Usar

Utilice estas transacciones cuando llegue efectivo a su cuenta de bróker como rendimiento de un activo:

- **Dividendo**: Ingresos provenientes de renta variable (acciones, ETF de distribución).
- **Interés**: Ingresos provenientes de instrumentos de renta fija (bonos, cuentas de ahorro, préstamos P2P, crowdfunding).

*No utilice estas transacciones para el retorno del principal (por ejemplo, la liquidación al vencimiento de un bono).*

---

## 💰 Dividendos en Detalle

### Evento vs Transacción

| Concepto | Evento de Dividendo | Transacción de Dividendo |
|---------|---------------|---------------------|
| **Alcance** | Global — afecta el precio del activo | Personal — afecta su cartera |
| **Ejemplo** | "Apple declaró $0.25/acción" | "Recibí $12.50 por mis 50 acciones" |
| **Registrado por** | Proveedor o manual (editor de datos) | Informe del bróker (importación BRIM) |
| **Impacto en gráfico** | Marcador de diamante (◆) en el gráfico de precios | No visible en el gráfico |

### Monto del Dividendo

El monto recibido depende del número de acciones mantenidas en la **fecha de registro**:

$$
\text{Dividendo Recibido} = \text{Acciones Mantenidas} \times \text{Dividendo por Acción}
$$

### Retención de Impuestos

Muchas jurisdicciones aplican una **retención fiscal** sobre los dividendos, especialmente para acciones extranjeras. El impuesto se deduce en la fuente:

$$
\text{Dividendo Neto} = \text{Dividendo Bruto} \times (1 - \tau_{withholding})
$$

El monto retenido se registra normalmente como una transacción de `TAX` independiente en LibreFolio, manteniendo el dividendo bruto y la deducción fiscal diferenciados para fines de reporte.

---

## 📈 Fuentes de Intereses

| Fuente | Descripción | Frecuencia |
|--------|-------------|-----------|
| **Cupones de bonos** | Pagos de tasa fija o flotante | Semestral / Anual |
| **Intereses de ahorro** | Intereses sobre depósitos en efectivo | Mensual / Trimestral |
| **Pagos de préstamos P2P** | Porción de intereses de los reembolsos del préstamo | Mensual |
| **Rendimientos de crowdfunding** | Rendimientos de tasa fija sobre proyectos | Varía |

!!! tip "Theory & formulas"

    Para las matemáticas del devengo de intereses (simple vs compuesto, convenciones de conteo de días, métricas de rendimiento), consulte:

    - **[📈 Eventos de Interés](../asset-events/interest.md)** — Mecánica de devengo e impacto en el precio
    - **[📅 Convenciones de Conteo de Días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de interés

---

## 🔗 Relacionados

- 💰 **[Eventos de Dividendo](../asset-events/dividend.md)** — Cómo afectan los dividendos a los precios de los activos
- 📈 **[Eventos de Interés](../asset-events/interest.md)** — Mecánica de devengo y cupones
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Tratamiento fiscal del rendimiento
- 🏛️ **[Bonos](../asset-types/bonds.md)** — El principal activo generador de intereses
- 📈 **[Acciones](../asset-types/stocks.md)** — La principal clase de activos que paga dividendos
