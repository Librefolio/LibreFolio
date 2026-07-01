# 💸 Capital Depositado, PnL Total y Pools de Efectivo

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](index.md)*

## 💡 Descripción General del Concepto

**Capital Depositado** = capital externo neto acumulado aportado desde el inicio:

$$
\mathrm{DepCap}(t) = \sum_{\tau \leq t} D(\tau) - \sum_{\tau \leq t} W(\tau)
$$

**PnL Total** = todo el valor generado por encima de las contribuciones externas:

$$
\boxed{\mathrm{TotalPnL}(t) = \mathrm{NAV}(t) - \mathrm{DepCap}(t)}
$$

---

## 🎯 Qué se contabiliza

| Transacción | Efecto en DepCap |
|------------|-----------------|
| DEPÓSITO / RETIRO (sin vincular) | ✅ Sí |
| TRANSFERENCIA DE EFECTIVO vinculado-externo | ✅ Sí |
| TRANSFERENCIA DE EFECTIVO vinculado-interno | ❌ No |
| COMPRA, VENTA, DIVIDENDO, INTERÉS, COMISIÓN, IMPUESTO | ❌ No |

---

## 📊 Modelo de Efectivo de Tres Pools

El Gráfico de Crecimiento descompone el efectivo actual en dos agregados visibles más un rastreador global oculto:

$$
\mathrm{Cash}(t) \approx \sum_b K_b(t) + \sum_b R_b(t)
$$

| Pool | Alcance | Significado |
|------|-------|---------|
| $K_b$ | Por bróker | Capital externo que aún permanece en el bróker $b$ |
| $R_b$ | Por bróker | Rendimientos generados que aún permanecen en el bróker $b$ |
| $W$ | Global | Rendimientos que salieron del sistema (restaurables en caso de redepósito) |

!!! info "Propiedades clave"

    - $\mathrm{DepCap}$ = suma histórica de todos los flujos. $\sum K_b$ = cuánto del efectivo actual es capital externo. Ambos divergen después de una COMPRA/VENTA.
    - Una COMPRA en el bróker $b_1$ solo consume $R_{b_1}$, nunca $R_{b_2}$.
    - Las transferencias de efectivo entre brókers mueven $R$ y $K$ desde el origen al destino sin afectar a $W$.

🔗 Reglas completas de actualización por bróker: **[Portfolio Engine — §6 Modelo de Efectivo de Tres Pools](portfolio-engine.md#6-modelo-de-efectivo-de-tres-pools-por-broker-k_b-r_b-w)**

---

## 📝 Ejemplos Prácticos

### A — Depósito → Compra → Venta con Ganancia

| Paso | Tx | $K$ | $R$ | Cash |
|------|----|-----|-----|------|
| 1 | DEPÓSITO €1.000 | 1.000 | 0 | 1.000 |
| 2 | COMPRA €1.000 | 0 | 0 | 0 |
| 3 | VENTA P=€1.200, C=€1.000 | 1.000 | 200 | 1.200 |

TotalPnL = 1.200 − 1.000 = **+€200** ✓

### B — Dividendo y luego Retirada

| Paso | Tx | $K$ | $R$ | $W$ | Cash |
|------|----|-----|-----|-----|------|
| 1 | DEPÓSITO €1.000 | 1.000 | 0 | 0 | 1.000 |
| 2 | DIVIDENDO €50 | 1.000 | 50 | 0 | 1.050 |
| 3 | RETIRO €100 (K primero) | 900 | 50 | 0 | 950 |
| 4 | RETIRO €950 (K=900→0, R=50→0, W+=50) | 0 | 0 | 50 | 0 |
| 5 | RE-DEPÓSITO €30 (restaurar min(30,W=50)=30) | 0 | 30 | 20 | 30 |

Después del paso 5: Cash=30, K=0, R=30 ✓ (rendimientos restaurados desde W)

### C — Reversión de Venta Total

| Paso | Tx | $K$ | $R$ | Cash |
|------|----|-----|-----|------|
| 1 | DEPÓSITO €1.000, COMPRA 1 a €1.000 | 0 | 0 | 0 |
| 2 | VENTA 1 a €1.005 (C=1.000, G=5) | 1.000 | 5 | 1.005 |

El capital regresa correctamente a $K$; solo la ganancia de €5 va a $R$. **No** van los €1.005 completos a $R$.

---

## ⚙️ Implementación

El modelo de 3 pools se ejecuta en un **único ciclo por transacción** (basado en eventos, no en delta diario):

1. Leer PMP antes de la mutación del pool
2. Actualizar K/R/W según las reglas del tipo de transacción
3. Luego reducir el pool PMP (para las VENTAS)

🔗 Ver **[Portfolio Engine — §6](portfolio-engine.md#6-modelo-de-efectivo-de-tres-pools-por-broker-k_b-r_b-w)** para todas las reglas formales.

---

## 🔗 Relacionados

- 💼 [NAV](nav.md) — el otro término en el PnL Total
- 📊 [Period PnL](period-pnl.md) — versión basada en ventanas temporales
- ⚙️ [Portfolio Engine](portfolio-engine.md) — modelo matemático completo
