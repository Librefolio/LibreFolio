# ![](../../../static/icons/asset-types/stock.png){: width="32" style="vertical-align: middle;" } Acciones

Una **acción** (o participación / capital) representa la propiedad parcial de una empresa que cotiza en bolsa. Cuando compras una acción, te conviertes en accionista con un derecho proporcional sobre los activos y las ganancias de la empresa.

---

## 🔑 Características Clave

| Propiedad | Detalle |
|----------|--------|
| **Código en LibreFolio** | `STOCK` |
| **Precios** | Cotizaciones en tiempo real o diferidas de las bolsas (NYSE, NASDAQ, LSE, etc.) |
| **Moneda** | Denominada en la moneda local de la bolsa |
| **Dividendos** | Muchas acciones pagan dividendos en efectivo periódicamente (trimestrales en EE. UU., semestrales en Europa) |
| **Splits** | Las empresas pueden dividir las acciones (ej. 4:1) para reducir el precio por acción |
| **Proveedores típicos** | Yahoo Finance, CSS Scraper |

---

## 📊 Cómo Funcionan las Acciones

1. **Determinación de precios**: Las acciones se negocian en bolsas públicas durante el horario de mercado. El precio refleja la oferta y la demanda.
2. **Dividendos**: Las empresas pueden distribuir una parte de los beneficios a los accionistas. Esto crea un [Evento de Dividendo](../asset-events/dividend.md) en la fecha ex-dividendo.
3. **Plusvalías**: La diferencia entre el precio de compra y el de venta determina tu ganancia o pérdida. Consulte [Tributación](../../fundamentals/taxation.md).
4. **Splits**: Una empresa puede dividir sus acciones para mejorar la liquidez. Un split 4:1 significa que cada acción se convierte en 4 acciones al ¼ del precio. Consulte [Evento de Split](../asset-events/split.md).

---

## 📐 Rentabilidad Total

La rentabilidad total de una acción incluye tanto la revalorización del precio como los dividendos:

$$
R_{total} = \frac{P_{end} - P_{start} + \sum D_i}{P_{start}}
$$

donde $D_i$ son todos los pagos de dividendos recibidos durante el periodo de posición.

---

## 🔗 Relacionado

- 💰 **[Eventos de Dividendo](../asset-events/dividend.md)** — Cómo afectan los dividendos a los precios de las acciones
- ✂️ **[Eventos de Split](../asset-events/split.md)** — Splits directos e inversos
- 📈 **[Rentabilidades y Tasas de Crecimiento](../../fundamentals/returns.md)** — Medición del rendimiento de las acciones
