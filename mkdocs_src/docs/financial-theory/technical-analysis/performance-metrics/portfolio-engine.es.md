# ⚙️ Motor de Cartera — Modelo Matemático

*[⬅️ Volver a la Descripción General de Métricas de Rendimiento](index.md)*

## 💡 Descripción General

Esta página define formalmente el modelo matemático que sustenta el motor de cálculo de cartera de LibreFolio. Todas las demás páginas de métricas ([NAV](nav.md), [Book Value](book-value.md), [Period P&L](period-pnl.md), [PMP](weighted-average-cost.md), [Deposited Capital](deposited-capital.md)) hacen referencia a esta página para sus reglas de cómputo precisas.

---

## 📐 1. Notación y Conjuntos

| Símbolo | Significado |
|--------|---------|
| $V(u)$ | Todos los brókers visibles para el usuario $u$ |
| $S \subseteq V(u)$ | Ámbito de brókers seleccionados (filtrados) |
| $A$ | Conjunto de activos con posiciones |
| $C^*$ | Moneda objetivo |
| $[t_0, t_1]$ | Marco de evaluación solicitado |
| $q(a,b,t)$ | Cantidad del activo $a$ en el bróker $b$ en la fecha $t$ |
| $p(a,t)$ | Precio de valoración del activo $a$ en la fecha $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Tipo de cambio de la moneda $c_1$ a $c_2$ en la fecha $t$ |

---

## 📐 2. Precio de Valoración

$$
p(a, t) = \begin{cases}
p_{\text{mkt}}(a, t) & \text{si PriceHistory} \leq t \text{ existe} \\
p_{\text{buy}}(a, t) & \text{si existe la última compra (BUY) de } V(u) \\
\varnothing & \text{en caso contrario (excluido del NAV)}
\end{cases}
$$

- $p_{\text{mkt}}$ = relleno hacia atrás (backward-fill) desde PriceHistory (último cierre con fecha $\leq t$)
- $p_{\text{buy}}$ = precio unitario de la compra (BUY) más reciente de $a$ en todos los brókers de $V(u)$, con fecha $\leq t$
- El PMP **nunca** se utiliza como precio de valoración

---

## 📐 3. Estado de la Posición

Para cada posición $(a, b)$ con $q(a,b,t) > 0$:

$$
\mathrm{MV}(a,b,t) = q(a,b,t) \cdot p(a,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_p, C^*, t\bigr)
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t) \cdot \mathrm{fx}\bigl(\mathrm{ccy}_w, C^*, t\bigr)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Donde $w(a,b,t)$ es el [precio medio ponderado (PMP)](weighted-average-cost.md) para la posición $(a,b)$ en la fecha $t$.

---

## 📐 4. Actualización Iterativa del PMP

Mantenido por posición $(a,b)$ con estado de pool $(\hat{q}, \hat{c})$:

**Adquisición** (qty $> 0$, costo unitario $u$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + u \cdot q_{\text{tx}}, \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

**Reducción** (qty $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

!!! info "Orden"

    Dentro de la misma fecha: las adiciones se procesan antes que las reducciones. Esto asegura que las ventas (VENTA) lean el PMP correcto, incluyendo las compras (COMPRA) del mismo día.

---

## 📐 5. Agregación de Cartera

$$
\mathrm{MV}(t) = \sum_{(a,b) \in S} \mathrm{MV}(a,b,t)
$$

$$
\mathrm{NAV}(t) = \mathrm{MV}(t) + \mathrm{Cash}(t) + \mathrm{InTransit}(t)
$$

$$
\mathrm{Book}(t) = \mathrm{OCB}(t) + \mathrm{Cash}(t) + \mathrm{InTransitBook}(t)
$$

$$
\mathrm{UGL}(t) = \mathrm{NAV}(t) - \mathrm{Book}(t)
$$

---

## 📐 6. Modelo de Efectivo de Tres Pools — Por Bróker $(K_b, R_b, W)$

Tres pools acumuladores rastrean la procedencia del efectivo. $K$ y $R$ se mantienen **por bróker** $b$; $W$ es global (sale completamente del sistema).

| Pool | Ámbito | Significado |
|------|-------|---------|
| $K_b$ | Por bróker | Capital externo que aún permanece en el bróker $b$ como efectivo |
| $R_b$ | Por bróker | Retornos generados que aún permanecen en el bróker $b$ como efectivo |
| $W$ | Global | Retornos que salieron del sistema (ocultos, recuperables al redepositar) |

!!! info "Propiedad clave"

    Una compra (BUY) en el bróker $b_1$ solo puede consumir $R_{b_1}$, nunca $R_{b_2}$. El efectivo no se teletransporta entre brókers; solo las transferencias explícitas mueven los saldos de los pools.

### Reglas de actualización (por transacción en el bróker $b$, cronológicas)

| Icono y Tipo | Fórmulas de Actualización | Lógica y Descripción |
|:---:|---|---|
| ![](../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPÓSITO**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Restaura primero los rendimientos previamente retirados del tracker global $W$ antes de añadir el resto al capital $K_b$. |
| ![](../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**RETIRO**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$ <br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consume primero el capital $K_b$, luego mueve los rendimientos restantes $\rho$ al tracker global $W$. |
| ![](../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDO / INTERÉS**<br>$I > 0$ | $R_b \mathrel{+}= I$ | Los rendimientos incrementan directamente el pool de rendimientos $R_b$. |
| ![](../../../static/icons/transactions/fee.png){: width="24" } ![](../../../static/icons/transactions/tax.png){: width="24" }<br>**COMISIÓN / IMPUESTO**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consume primero los rendimientos $R_b$; si $R_b$ se vuelve negativo, se detrae del capital $K_b$. |
| ![](../../../static/icons/transactions/buy.png){: width="24" }<br>**COMPRA**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consume primero los rendimientos $R_b$, luego retira el resto del capital $K_b$. |
| ![](../../../static/icons/transactions/sell.png){: width="24" }<br>**VENTA** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | La base de costo $C = |q_s| \cdot w_{\text{pre}}$ vuelve al capital $K_b$; la ganancia $G$ va a los rendimientos $R_b$ (si $G < 0$, se comporta como una comisión).<br><br>!!! warning "Orden crítico"<br><br>    $C$ debe computarse **antes** de que se reduzca el pool de PMP (de lo contrario, una venta total daría $C = 0$). |
| ![](../../../static/icons/transactions/cash-transfer.png){: width="24" }<br>**TRANSFERENCIA DE EFECTIVO**<br>(Interna, $s \to d$, $X > 0$) | **Extremo de salida ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Extremo de llegada ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho$ | Las transferencias internas de efectivo mueven las asignaciones de los pools ($R_s \to R_d$, $K_s \to K_d$) proporcionalmente al saldo de salida.<br>El tracker global $W$ **nunca** es afectado (el capital permanece en el sistema). |

Si las fechas de salida y llegada difieren, la transferencia está en tránsito: se resta de $s$ el día de salida y se suma a $d$ el día de llegada. Entre esas fechas, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ por el monto en tránsito, lo cual se maneja mediante una conciliación proporcional.

### Agregación para salida

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### Invariante de conciliación

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Se aplica un escalado proporcional por bróker si la deriva es $> 0.01$ (debido al redondeo de FX o al tiempo de tránsito).

---

## 📐 7. Contribución del Periodo

Para el periodo $[t_0, t_1]$, por posición $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{Fees}(a,b)
$$

Conjunto de posiciones de contribución:

$$
\mathcal{P} = \mathcal{P}(t_0) \cup \mathcal{P}(t_1) \cup \mathrm{keys}(\text{Realized}) \cup \mathrm{keys}(\text{Income}) \cup \mathrm{keys}(\text{Fees})
$$

Lo no asignado (comisiones/ingresos sin `asset_id`) se agrupa por bróker.

---

## 📐 8. Ganancia/Pérdida Realizada

En una venta (SELL) de $|q_s|$ unidades de la posición $(a,b)$:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b) \cdot \mathrm{fx}(\mathrm{ccy}_w, C^*, t)
$$

$$
\mathrm{Realized} = P_{\text{sell}} - C
$$

Donde $w_{\text{pre}}$ es el PMP **antes** de la reducción del pool (mismo valor utilizado por la regla de VENTA de 3 pools anterior).

---

## 📐 9. Arquitectura Pre-Frame / Frame

| Fase | Rango de fechas | Computa |
|-------|-----------|----------|
| Pre-frame | $[t_{\mathrm{first}},\ t_0)$ | Efectivo, qty, PMP, pools — sin evaluación de mercado |
| Frame | $[t_0,\ t_1]$ | Diario completo: precios, FX, estados de posición, estados de cartera |

Las transacciones de pre-frame actualizan los acumuladores (libro de efectivo, pools de PMP, K/R/W de 3 pools) sin consumir datos de precios o FX. Esto permite una caché eficiente basada en rangos.

---

## 📐 10. Métricas de Rendimiento (Capa 2)

Computadas **después** de los estados diarios, como una pasada separada:

| Métrica | Fórmula | Referencia |
|--------|---------|-----------|
| PnL Total | $\mathrm{NAV}(t) - \text{DepositedCapital}(t)$ | [Deposited Capital](deposited-capital.md) |
| PnL del Periodo | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [Period P&L](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (cadena de sub-periodos) | [TWRR](twrr.md) |
| MWRR | XIRR resolviendo $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| ROI Simple | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Efecto de Tiempo | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Timing Effect](timing-effect.md) |

---

## 🔗 Relacionado

- 💼 [NAV](nav.md) — valoración de instantánea
- 📖 [Book Value](book-value.md) — agregado de la base de costo
- 📊 [Period P&L](period-pnl.md) — ganancia/pérdida en ventana con contribución
- 💸 [Deposited Capital](deposited-capital.md) — detalles de los 3 pools y ejemplos resueltos
- 📈 [PMP](weighted-average-cost.md) — método de costo iterativo
