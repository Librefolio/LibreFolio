# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Las plataformas de **P2P / Crowdfunding** permiten a los inversores participar en proyectos inmobiliarios o préstamos al consumo/empresariales con cantidades relativamente pequeñas. Estos instrumentos suelen ofrecer pagos de intereses fijos o variables y tienen una fecha de vencimiento definida.

---

## 🔑 Características Clave

| Propiedad | Detalle |
|----------|--------|
| **Código en LibreFolio** | `CROWDFUND` |
| **Valoración** | No cotiza en bolsa — el valor suele ser el principal invertido |
| **Moneda** | Denominado en la moneda de operación de la plataforma |
| **Ingresos** | Pagos de intereses periódicos (mensuales, trimestrales o al vencimiento) |
| **Liquidez** | Muy baja — los fondos están bloqueados hasta el vencimiento o la recompra |
| **Proveedores típicos** | Scheduled Investment, Manual |

---

## 📊 Cómo Funciona

### 🏗️ Crowdfunding Inmobiliario

1. Una plataforma publica un proyecto inmobiliario que necesita financiación
2. Múltiples inversores aportan cantidades pequeñas (típicamente entre 500 € y 10.000 €)
3. El proyecto paga intereses sobre el capital invertido
4. Al vencimiento, se devuelve el principal (si el proyecto tiene éxito)

### 💸 Préstamos P2P

1. Los prestatarios solicitan préstamos a través de una plataforma
2. Los inversores financian partes de los préstamos
3. Los prestatarios devuelven el principal + los intereses durante el plazo del préstamo
4. La plataforma distribuye los pagos a los inversores

---

## ⚠️ Factores de Riesgo

| Riesgo | Descripción |
|------|-------------|
| **Riesgo de impago** | El prestatario o el proyecto pueden incumplir sus obligaciones de pago |
| **Riesgo de liquidez** | No se puede vender antes del vencimiento (a diferencia de las acciones) |
| **Riesgo de plataforma** | La propia plataforma puede ir a la quiebra |
| **Riesgo de concentración** | Cada inversión es un único proyecto o prestatario |

---

## 🔧 Modelado en LibreFolio

El proveedor **Scheduled Investment** está diseñado para estos instrumentos. Genera:

- **[Eventos de interés](../asset-events/interest.md)** — Pagos de cupones periódicos basados en la tasa y el calendario configurados
- **[Eventos de liquidación al vencimiento](../asset-events/maturity-settlement.md)** — Devolución final del capital al final del plazo
- **[Eventos de ajuste de precio](../asset-events/price-adjustment.md)** — Ajustes a la baja si el proyecto tiene un rendimiento inferior al esperado

---

## 🔗 Relacionado

- 📈 **[Eventos de Interés](../asset-events/interest.md)** — Cómo funciona el devengo de intereses
- 🏁 **[Liquidación al Vencimiento](../asset-events/maturity-settlement.md)** — Devolución del capital al vencimiento del activo
- 📅 **[Convenciones de Recuento de Días](../../fundamentals/day-count.md)** — Cómo se calculan los periodos de interés
