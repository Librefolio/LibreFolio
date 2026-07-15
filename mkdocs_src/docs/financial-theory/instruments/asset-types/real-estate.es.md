# ![](../../../static/icons/asset-types/crowdfunding.png){: width="32" style="vertical-align: middle;" } P2P / Crowdfunding

Las plataformas **P2P / Crowdfunding** permiten a los inversores participar en proyectos inmobiliarios o préstamos al consumo/empresariales con cantidades relativamente pequeñas. Estos instrumentos suelen ofrecer pagos de intereses fijos o variables y tienen una fecha de vencimiento definida.

---

## 🔑 Características clave

| Propiedad | Detalle |
|-----------|---------|
| **Código en LibreFolio** | `CROWDFUND` |
| **Valoración** | No cotiza en bolsa — el valor es típicamente el principal invertido |
| **Divisa** | Denominada en la moneda operativa de la plataforma |
| **Rendimiento** | Pagos periódicos de intereses (mensuales, trimestrales o al vencimiento) |
| **Liquidez** | Muy baja — los fondos están bloqueados hasta el vencimiento o recompra |
| **Proveedores típicos** | Inversión programada, Manual |

---

## 📊 Cómo funciona

### 🏗️ Crowdfunding Inmobiliario

1. Una plataforma lista un proyecto inmobiliario que necesita financiación
2. Múltiples inversores aportan pequeñas cantidades (típicamente de €500 a €10,000)
3. El proyecto paga intereses sobre el capital invertido
4. Al vencimiento, el principal se devuelve (si el proyecto tiene éxito)

### 💸 Préstamos P2P

1. Los prestatarios solicitan préstamos a través de una plataforma
2. Los inversores financian partes de los préstamos
3. Los prestatarios devuelven el principal más los intereses durante el plazo del préstamo
4. La plataforma distribuye los pagos a los inversores

---

## ⚠️ Factores de riesgo

| Riesgo | Descripción |
|--------|-------------|
| **Riesgo de impago** | El prestatario/proyecto puede no devolver el préstamo |
| **Riesgo de liquidez** | No se puede vender antes del vencimiento (a diferencia de las acciones) |
| **Riesgo de plataforma** | La propia plataforma puede quebrar |
| **Riesgo de concentración** | Cada inversión es un único proyecto/prestatario |

---

## 🔧 Modelado en LibreFolio

El proveedor **Inversión programada** está diseñado para estos instrumentos. Genera:

- **[Eventos de Interés](../asset-events/interest.md)** — Pagos periódicos de cupones basados en la tasa y el cronograma configurados
- **[Eventos de Liquidación al Vencimiento](../asset-events/maturity-settlement.md)** — Devolución del capital final al término del plazo
- **[Eventos de Ajuste de Precio](../asset-events/price-adjustment.md)** — Reducciones de valor si el proyecto tiene un rendimiento inferior al esperado

---

## 🔗 Relacionados

- 📈 **[Eventos de Interés](../asset-events/interest.md)** — Cómo funciona la acumulación de intereses
- 🏁 **[Liquidación al Vencimiento](../asset-events/maturity-settlement.md)** — Devolución del capital al final de la vida útil
- 📅 **[Convenciones de Cómputo de Días](../../fundamentals/day-count.md)** — Cómo se calculan los períodos de interés
