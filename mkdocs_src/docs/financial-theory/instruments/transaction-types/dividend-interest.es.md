# ![](../../../static/icons/transactions/dividend.png){: width="32" style="vertical-align: middle;" } Dividendo e interés ![](../../../static/icons/transactions/interest.png){: width="32" style="vertical-align: middle;" }

<div class="screenshot-container">
 <img class="gallery-img" data-category="transactions" data-name="form-modal-dividend" alt="Formulario de Transacción — DIVIDENDO">
</div>

Los **dividendos** y los **intereses** representan el rendimiento generado por los activos de su cartera. Son pagos en efectivo recibidos sin vender el activo subyacente.

---

## 🔑 Propiedades Clave

| Propiedad | Dividendo | Interés |
|-----------|-----------|---------|
| **Código** | `DIVIDEND` | `INTEREST` |
| **Efecto en efectivo** | ⬆️ Aumenta el saldo | ⬆️ Aumenta el saldo |
| **Efecto en activo** | — (cantidad sin cambios) | — (principal sin cambios) |
| **Evento fiscal** | Sí (ingreso gravable) | Sí (ingreso gravable) |

---

## 💡 Cuándo Usar

Utilice estas transacciones cuando el efectivo llegue a su cuenta de corretaje como rendimiento de un activo:

- **Dividendo**: Ingreso de patrimonio (acciones, ETFs distribuidores).
- **Interés**: Ingreso de instrumentos de renta fija (bonos, cuentas de ahorro, préstamos P2P, crowdfunding).

*No utilice estas transacciones para la devolución del principal (por ejemplo, liquidación de vencimiento de bonos).*

---

## 💰 Dividendos en Detalle

### Evento vs Transacción

| Concepto | Evento de Dividendo | Transacción de Dividendo |
|----------|---------------------|--------------------------|
| **Alcance** | Global — afecta el precio del activo | Personal — afecta su cartera |
| **Ejemplo** | "Apple declaró $0.25/acción" | "Recibí $12.50 de mis 50 acciones" |
| **Registrado por** | Proveedor o manual (Editor de Datos) | Informe del bróker (importación BRIM) |
| **Impacto en gráfico** | Marcador de diamante (◆) en el gráfico de precios | No visible en el gráfico |

### Monto del Dividendo

El monto recibido depende del número de acciones poseídas en la **fecha de registro**:

$$
\text{Dividendo Recibido} = \text{Acciones Poseídas} \times \text{Dividendo por Acción}
$$

### Retención de Impuestos

Muchas jurisdicciones aplican **retención de impuestos** sobre los dividendos — especialmente para acciones extranjeras. El impuesto se deduce en origen:

$$
\text{Dividendo Neto} = \text{Dividendo Bruto} \times (1 - \tau_{retención})
$$

El monto retenido típicamente se registra como una transacción separada de `TAX` en LibreFolio, manteniendo el dividendo bruto y la deducción del impuesto diferenciados para fines de reporte.

---

## 📈 Fuentes de Interés

| Fuente | Descripción | Frecuencia |
|--------|-------------|------------|
| **Cupones de bonos** | Pagos de tasa fija o variable | Semestral / Anual |
| **Interés de ahorro** | Interés sobre depósitos en efectivo | Mensual / Trimestral |
| **Pagos de préstamos P2P** | Porción de interés en amortizaciones de préstamos | Mensual |
| **Rendimientos de crowdfunding** | Rendimientos de tasa fija en proyectos | Variable |

!!! tip "Teoría y fórmulas"

    Para las matemáticas de la acumulación de intereses (simple vs compuesto, convenciones de conteo de días, métricas de rendimiento), consulte:

    - **[📈 Eventos de Interés](../asset-events/interest.md)** — Mecánica de acumulación e impacto en el precio
    - **[📅 Convenciones de Conteo de Días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de interés

---

## 🔗 Relacionados

- 💰 **[Eventos de Dividendo](../asset-events/dividend.md)** — Cómo los dividendos afectan los precios de los activos
- 📈 **[Eventos de Interés](../asset-events/interest.md)** — Mecánica de acumulación y cupones
- 🔬 **[Análisis de Lotes FIFO](../../technical-analysis/performance-metrics/fifo-engine/fifo-lot-analysis.md#income-allocation-across-lots)** — Cómo se asigna el ingreso prorrateado entre lotes abiertos
- 💰 **[Tributación](../../fundamentals/taxation.md)** — Tratamiento fiscal del rendimiento
- 🏛️ **[Bonos](../asset-types/bonds.md)** — El principal activo generador de intereses
- 📈 **[Acciones](../asset-types/stocks.md)** — La principal clase de activo pagadora de dividendos
