# ⚙️ Motor de Cartera — Modelo Matemático

## 💡 Resumen

Esta página define formalmente el modelo matemático que subyace al motor de cálculo de carteras de LibreFolio. Todas las demás páginas de métricas ([NAV](nav.md), [Valor contable](book-value.md), [P&L período](period-pnl.md), [Rendimiento sobre coste](yield-on-cost.md), [PMC](../weighted-average-cost.md), [Capital depositado](deposited-capital.md)) hacen referencia a esta página para sus reglas de cálculo precisas.

---

## 📐 1. Notación y conjuntos

| Símbolo | Significado |
|--------|---------|
| $V(u)$ | Todos los brókers visibles para el usuario $u$ |
| $S \subseteq V(u)$ | Ámbito de brókers seleccionado (filtrado) |
| $A$ | Conjunto de activos con posiciones |
| $C^*$ | Moneda objetivo |
| $[t_0, t_1]$ | Marco de evaluación solicitado |
| $q(a,b,t)$ | Cantidad del activo $a$ en el bróker $b$ en la fecha $t$ |
| $p(a,t)$ | Precio de valoración del activo $a$ en la fecha $t$ |
| $\mathrm{fx}(c_1, c_2, t)$ | Tipo de cambio de la moneda $c_1$ a $c_2$ en la fecha $t$ |

---

## 📐 2. Precio de valoración {: #2-valuation-price }

$$
\operatorname{mark}(a,t)=
\begin{cases}
\text{MARKET}(a,t) & \text{cotización del sistema de activos del mismo día}\\
\operatorname{avg}(\text{TRADE}(a,t)) & \text{observaciones de COMPRA/VENTA/AJUSTE con precio del mismo día}\\
\text{última observación antes de }t & \text{arrastrado (LOCF)}\\
\varnothing & \text{sin observación en }t\text{ o antes}
\end{cases}
$$

- El resolutor unificado es el único cerebro de valoración: `MARKET → TRADE_AVG → CARRIED → MISSING`.
- `CARRIED` es la última observación arrastrada (LOCF). Transporta metadatos de antigüedad `days_back`.
- `estimated=True` significa origen TRADE. Una cotización MARKET arrastrada obsoleta está obsoleta, no estimada.
- Las valoraciones permanecen en moneda nativa; cada consumidor convierte a $C^*$ en la fecha de valoración $t$.
- La conversión FX del coste base permanece fijada a la fecha de la transacción.
- El PMC **nunca** se usa como precio de valoración.

Consulte [Resolución de precios](price-resolution.md) para conocer el contrato del resolutor y la semántica de calidad de datos.

---

## 📐 3. Estado de la posición {: #3-position-state }

Para cada posición $(a, b)$ con $q(a,b,t) > 0$:

$$
\mathrm{MV}(a,b,t) =
\frac{q(a,b,t)}{qbq(a)}\cdot
\operatorname{mark}(a,t)\cdot
\mathrm{fx}\bigl(\mathrm{ccy}_{mark}, C^*, t\bigr)
$$

$$
\mathrm{CB}(a,b,t) = q(a,b,t) \cdot w(a,b,t)
$$

$$
\mathrm{UGL}(a,b,t) = \mathrm{MV}(a,b,t) - \mathrm{CB}(a,b,t)
$$

Donde $w(a,b,t)$ es el [precio medio de compra (PMC)](../weighted-average-cost.md) para la posición $(a,b)$ en la fecha $t$, mantenido en $C^*$ a tipos de cambio históricos (§4): el coste base no toma tipo de cambio en $t$, por lo que para un activo extranjero el efecto del tipo de cambio es parte de $\mathrm{UGL}$.

---

## 📐 4. Actualización iterativa del PMC

Mantenido por posición $(a,b)$ con estado de fondo $(\hat{q}, \hat{c})$, el coste $\hat{c}$ mantenido en $C^*$:

**Adquisición** (cantidad $> 0$, importe $P$ pagado en la moneda $c$ en la fecha $d$):

$$
\hat{q}_{\text{new}} = \hat{q} + q_{\text{tx}}, \quad
\hat{c}_{\text{new}} = \hat{c} + P \cdot \mathrm{fx}(c, C^*, d), \quad
w = \frac{\hat{c}_{\text{new}}}{\hat{q}_{\text{new}}}
$$

$P$ es el efectivo pagado por una COMPRA, o la sobrescritura del coste base por unidad multiplicada por $q_{\text{tx}}$ para una TRANSFERENCIA o AJUSTE; $\mathrm{fx}(C^*, C^*, d) = 1$. Cuando no existe un tipo de cambio en $d$ o antes, o la adquisición no tiene coste base, la cantidad entra y el coste no: el coste de la posición se marca como incompleto en lugar de contar como cero.

**Reducción** (cantidad $< 0$):

$$
w_{\text{pre}} = \frac{\hat{c}}{\hat{q}}, \quad
\hat{q}_{\text{new}} = \hat{q} - |q_{\text{tx}}|, \quad
\hat{c}_{\text{new}} = \hat{q}_{\text{new}} \cdot w_{\text{pre}}
$$

**Desdoblamiento** (vinculado a un evento de desdoblamiento): $\hat{q}$ cambia, $\hat{c}$ no.

!!! info "Orden"

    Dentro de la misma fecha: las adiciones se procesan antes que las reducciones. Garantiza que la VENTA lea el PMC correcto, incluidas las COMPRAS del mismo día.

---

## 📐 5. Agregación de cartera {: #5-portfolio-aggregation }

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

## 📐 6. Modelo de efectivo de tres fondos — Por bróker $(K_b, R_b, W)$ {: #6-three-pool-cash-model-per-broker-k_b-r_b-w }

Tres fondos acumuladores rastrean la procedencia del efectivo. $K$ y $R$ se mantienen **por bróker** $b$; $W$ es global (sale del sistema por completo).

| Fondo | Ámbito | Significado |
|------|-------|---------|
| $K_b$ | Por bróker | Capital externo aún en el bróker $b$ como efectivo |
| $R_b$ | Por bróker | Rendimientos generados aún en el bróker $b$ como efectivo |
| $W$ | Global | Rendimientos que salieron del sistema (ocultos, restaurables al volver a depositar) |

!!! info "Propiedad clave"

    Una COMPRA en el bróker $b_1$ solo puede consumir $R_{b_1}$, nunca $R_{b_2}$. El efectivo no se teletransporta entre brókers — solo las transferencias explícitas mueven los saldos de los fondos.

### 🔁 Reglas de actualización (por transacción en el bróker $b$, cronológicas)

| Icono y tipo | Fórmulas de actualización | Lógica y descripción |
|:---:|---|---|
| ![](../../../../static/icons/transactions/deposit.png){: width="24" }<br>**DEPÓSITO**<br>$D > 0$ | $r = \min(D,\, W)$<br>$R_b \mathrel{+}= r$<br>$W \mathrel{-}= r$<br>$K_b \mathrel{+}= D - r$ | Restaura primero los rendimientos retirados previamente desde el rastreador global $W$, luego agrega el resto al capital $K_b$. |
| ![](../../../../static/icons/transactions/withdrawal.png){: width="24" }<br>**RETIRO**<br>$X > 0$ | $k = \min(X,\, K_b)$<br>$K_b \mathrel{-}= k$<br>$\rho = \min(X - k,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$W \mathrel{+}= \rho$ | Consume primero el capital $K_b$, luego mueve los rendimientos restantes $\rho$ al rastreador global $W$. |
| ![](../../../../static/icons/transactions/dividend.png){: width="24" } ![](../../../../static/icons/transactions/interest.png){: width="24" }<br>**DIVIDENDO / INTERÉS**<br>$I > 0$ | $R_b \mathrel{+}= I$ | Los rendimientos incrementan directamente el fondo de rendimientos $R_b$. |
| ![](../../../../static/icons/transactions/fee.png){: width="24" } ![](../../../../static/icons/transactions/tax.png){: width="24" }<br>**COMISIÓN / IMPUESTO**<br>$F > 0$ | $R_b \mathrel{-}= F$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b,\; R_b = 0$ | Consume primero los rendimientos $R_b$; si $R_b$ se vuelve negativo, se drena desde el capital $K_b$. |
| ![](../../../../static/icons/transactions/buy.png){: width="24" }<br>**COMPRA**<br>$B > 0$ | $\rho = \min(B,\, R_b)$<br>$R_b \mathrel{-}= \rho$<br>$K_b \mathrel{-}= (B - \rho)$ | Consume primero los rendimientos $R_b$, luego drena el resto desde el capital $K_b$. |
| ![](../../../../static/icons/transactions/sell.png){: width="24" }<br>**VENTA** | $G = P - C$<br>$K_b \mathrel{+}= C$<br>$R_b \mathrel{+}= G$<br>$\text{si } R_b < 0\text{: } K_b \mathrel{+}= R_b, \quad R_b = 0$ | El coste base $C = |q_s| \cdot w_{\text{pre}}$ vuelve al capital $K_b$; la ganancia $G$ va a los rendimientos $R_b$ (si $G < 0$, se comporta como una comisión).<br><br>!!! warning "Orden crítico"<br><br> $C$ debe calcularse **antes** de que se reduzca el fondo PMC (una venta total daría $C = 0$ de lo contrario). |
| ![](../../../../static/icons/transactions/cash-transfer.png){: width="24" }<br>**TRANSFERENCIA DE FONDOS**<br>(Interna, $s \to d$, $X > 0$) | **Tramo de salida ($s$):**<br>$\rho = \min(X,\, R_s)$<br>$R_s \mathrel{-}= \rho$<br>$\kappa = X - \rho$<br>$K_s \mathrel{-}= \kappa$<br><br>**Tramo de llegada ($d$):**<br>$K_d \mathrel{+}= \kappa$<br>$R_d \mathrel{+}= \rho$ | Las transferencias internas de fondos mueven las asignaciones de fondos ($R_s \to R_d$, $K_s \to K_d$) proporcionalmente al saldo de salida.<br>El rastreador global $W$ **nunca** se toca (el capital permanece dentro del sistema). |

Si las fechas de salida y llegada difieren, la transferencia está en tránsito: se resta de $s$ el día de salida y se suma a $d$ el día de llegada. Entre esas fechas, $\sum K_b + \sum R_b < \mathrm{Cash}_{\text{like}}$ por el monto en tránsito — gestionado mediante conciliación proporcional.

### 🧮 Agregación para la salida

$$
\mathrm{CashFromCapital}(t) = \sum_{b \in S} K_b(t)
$$

$$
\mathrm{CashFromReturns}(t) = \sum_{b \in S} R_b(t)
$$

### ⚖️ Invariante de conciliación

$$
\mathrm{Cash}_{\text{like}}(t) \approx \sum_{b \in S} K_b(t) + \sum_{b \in S} R_b(t)
$$

Se aplica un escalado proporcional por bróker si la desviación es $> 0.01$ (por redondeo de FX o temporización en tránsito).

---

## 📐 7. Contribución del período {: #7-period-contribution }

Para el período $[t_0, t_1]$, por posición $(a,b)$:

$$
\Delta\mathrm{UGL}(a,b) = \mathrm{UGL}(a,b,t_1) - \mathrm{UGL}(a,b,t_0)
$$

$$
\mathrm{PnL}(a,b) = \Delta\mathrm{UGL}(a,b) + \mathrm{Realized}(a,b) + \mathrm{Income}(a,b) - \mathrm{FeesTaxes}(a,b)
$$

Conjunto de posiciones de contribución:

$$
\mathcal{P} = \text{posiciones con actividad de COMPRA/VENTA/AJUSTE/TRANSFERENCIA o cantidad límite}
$$

El P&L período a nivel de cartera también expone un residuo:

$$
\mathrm{Other} =
\mathrm{PnL}_{period} - \Delta\mathrm{UGL} - \mathrm{Realized} - \mathrm{Income} + \mathrm{FeesTaxes}
$$

Las comisiones/ingresos no asignados sin `asset_id` se agrupan por bróker como otros efectos del período.

---

## 📐 8. P&L realizado

En una VENTA de $|q_s|$ unidades de la posición $(a,b)$ en la fecha $t$:

$$
C = |q_s| \cdot w_{\text{pre}}(a,b)
$$

$$
\mathrm{Realized} = P_{\text{sell}} \cdot \mathrm{fx}(\mathrm{ccy}_{\text{sell}}, C^*, t) - C
$$

Donde $w_{\text{pre}}$ es el PMC en $C^*$ **antes** de la reducción del fondo (el mismo valor usado por la regla de VENTA de 3 fondos anterior): las unidades vendidas salen a su coste histórico, sin conversión en la fecha de venta. Una venta cuyos ingresos no puedan convertirse, o que se extraiga de una posición cuyo coste esté incompleto, se deja fuera del P&L realizado.

---

## 📐 9. Arquitectura de pre-marco / marco

| Fase | Rango de fechas | Calcula |
|-------|-----------|----------|
| Pre-marco | $[t_{\mathrm{first}},\ t_0)$ | Efectivo, cantidad, PMC, fondos — sin evaluación de mercado |
| Marco | $[t_0,\ t_1]$ | Diario completo: precios, FX, estados de posición, estados de cartera |

Las transacciones de pre-marco actualizan los acumuladores (libro mayor de efectivo, fondos PMC, K/R/W de 3 fondos) sin consumir datos de precios o FX. Esto permite un almacenamiento en caché eficiente basado en rangos.

---

## 📐 10. Métricas de rendimiento (Capa 2)

Calculadas **después** de los estados diarios, como una pasada separada:

| Métrica | Fórmula | Referencia |
|--------|---------|-----------|
| P&L total | $\mathrm{NAV}(t) - \text{CapitalBaseline}(t)$ | [Capital depositado](deposited-capital.md) |
| P&L período | $\mathrm{NAV}(t_1) - \mathrm{NAV}(t_0) - \text{ECF}_{[t_0,t_1]}$ | [P&L período](period-pnl.md) |
| TWRR | $\prod_i (1 + r_i) - 1$ (cadena de subperíodos) | [TWRR](twrr.md) |
| MWRR | XIRR resolviendo $\sum \frac{CF_i}{(1+r)^{d_i/365}} = 0$ | [MWRR](mwrr.md) |
| ROI simple | $(\mathrm{NAV} - \text{NetInvested}) / \text{NetInvested}$ | [ROI](roi.md) |
| Rendimiento anualizado neto | $(1+r_{\mathrm{net}})^{365/d}-1$, suprimido por debajo de 30 días | [Rendimiento anualizado neto](net-annualized-return.md) |
| Rendimiento sobre coste | Ingreso bruto por transacción de los últimos 365 días por unidad histórica elegible, dividido por el PMC unitario residual en $t_1$ | [Rendimiento sobre coste](yield-on-cost.md) |
| Efecto timing | $\text{MWRR}_{\text{cum}} - \text{TWRR}_{\text{cum}}$ | [Efecto timing](timing-effect.md) |

---

## 🔗 Relacionado

- 💼 [NAV](nav.md) — valoración puntual
- 🧭 [Resolución de precios](price-resolution.md) — resolutor de valoración unificado
- 📈 [Rendimiento anualizado neto](net-annualized-return.md) — definiciones de CAGR de posiciones, período y FIFO
- 💸 [Rendimiento sobre coste](yield-on-cost.md) — ingreso bruto registrado acumulado relativo al PMC unitario residual
- 📖 [Valor contable](book-value.md) — agregado del coste base
- 📊 [P&L período](period-pnl.md) — ganancia/pérdida por ventana con contribución
- 💸 [Capital depositado](deposited-capital.md) — detalles de 3 fondos y ejemplos resueltos
- 📈 [PMC](../weighted-average-cost.md) — método iterativo de coste
- 📈 [Resumen de métricas de rendimiento](../index.md) — todas las métricas de rendimiento de un vistazo
