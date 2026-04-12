# <img src="../../../static/icons/transactions/interest.png" width="32" style="vertical-align: middle;" /> Intereses (Transacción)

Una **transacción de intereses** registra los ingresos por intereses recibidos de bonos, cuentas de ahorro, préstamos P2P u otros instrumentos de renta fija. Representa el impacto a nivel de cartera de un [evento de interés](../asset-events/interest.md).

---

## 🔑 Propiedades Clave

| Propiedad | Detalle |
|----------|--------|
| **Código** | `INTEREST` |
| **Efecto en caja** | ⬆️ Aumenta el saldo |
| **Efecto en el activo** | — (el capital permanece inalterado) |
| **Evento fiscal** | Sí (ingresos imponibles) |

---

## 📊 Fuentes de Intereses

| Fuente | Descripción | Frecuencia |
|--------|-------------|-----------|
| **Cupones de bonos** | Pagos de tasa fija o variable | Semestral / Anual |
| **Intereses de ahorro** | Intereses sobre depósitos de efectivo | Mensual / Trimestral |
| **Pagos de préstamos P2P** | Componente de intereses de los reembolsos del préstamo | Mensual |
| **Retornos de Crowdfunding** | Retornos de tasa fija sobre proyectos | Varía |

---

## 📐 Interés Simple vs Compuesto

### 📏 Interés Simple

Interés calculado únicamente sobre el capital original:

$$
I = P \times r \times t
$$

### 📈 Interés Compuesto

Interés calculado sobre el capital + los intereses acumulados:

$$
A = P \times (1 + r)^t
$$

La diferencia entre el interés simple y el compuesto es la base del benchmark de [Crecimiento Lineal vs Compuesto](../../technical-analysis/synthetic-benchmarks/index.md).

---

## 🔗 Relacionado

- 📈 **[Eventos de Interés](../asset-events/interest.md)** — Mecánica de devengo y cupones
- 🏛️ **[Bonos](../asset-types/bonds.md)** — El activo principal que genera intereses
- 📅 **[Convenciones de conteo de días](../../fundamentals/day-count.md)** — Cómo se calculan los periodos de interés
