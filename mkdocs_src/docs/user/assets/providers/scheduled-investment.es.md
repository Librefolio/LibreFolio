# <img src="../../../../static/scheduled_investment.png" alt=""> Inversión programada

El proveedor Inversión programada calcula el valor de un activo a partir de su calendario de intereses en lugar
de leer un precio de mercado. Úsalo para cuentas de ahorro, depósitos a plazo, préstamos P2P o de crowdfunding,
y bonos que sigas por su interés acumulado. En la lista **Proveedor** se llama
**Calculadora de inversión programada**.

## 🔍 Qué ofrece

- ✅ **Precio actual** e **historial**, calculados a partir de tu calendario: no se consulta ningún sitio web, y
  el mismo calendario siempre da los mismos valores.
- ✅ **Eventos**: con **Generar cupón**, pagos de intereses y una liquidación final al vencimiento, además
  de los eventos que añadas tú mismo.
- ❌ **Búsqueda** y **detalles**: no aplica. Tampoco hay un identificador que escribir: LibreFolio
  crea uno por ti.

## 📋 Editor de calendario de intereses {: #interest-schedule-editor }

Al elegir el proveedor en **Asignación de proveedor** se abre el editor **Calendario de intereses**. Comienza con
la configuración para todo el calendario:

- **Valor inicial** y **Moneda**: el importe invertido, o el valor nominal — p. ej. 10.000 EUR.
- **Tipo de interés**: **Simple** o **Compuesto** — consulta
  [Cómo se calcula el valor](#how-value-is-calculated).
- **Recuento de días**: cómo se cuentan los días de un año — **ACT/365**, **ACT/360**, **ACT/ACT** o
  **30/360**. Consulta [Convenciones de recuento de días](../../../financial-theory/fundamentals/day-count.md).

Luego añade los periodos con **Añadir primer periodo**, y **Añadir periodo** para los siguientes:

| Columna | Qué introducir |
|---|---|
| **Periodo** | Fecha de inicio y fin, ambas incluidas |
| **Tasa %** | La tasa anual como porcentaje: `5.00` significa 5 % al año |
| **Frecuencia** | Con qué frecuencia vence el interés: Diaria, Semanal, Mensual, Trimestral, Semestral o Anual |
| **Generar cupón** | Márcalo para pagar el interés acumulado en cada fecha de vencimiento |

Los periodos deben sucederse, sin huecos ni solapamientos. **Dividir** corta un periodo en dos; selecciona
periodos vecinos y haz clic en **Fusionar** para unirlos.

### ⚡ Interés de demora {: #late-interest }

Para un préstamo reembolsado con retraso, activa **⚡ Interés de demora** debajo de los periodos: el activo sigue creciendo
después de que termine el último periodo. Aparece una fila de demora con su propia **Tasa %**, **Frecuencia** y
**Generar cupón**. Haz clic en su periodo para establecer los días de gracia, y elige **Simple** o
**Compuesto** (predeterminado) junto al interruptor.

- Durante los días de gracia, el interés sigue acumulándose a la tasa del último periodo.
- Después de ellos, se aplica la tasa de demora.

### 📅 Eventos del activo

Añade eventos puntuales con **Añadir evento**: una **Fecha**, un **Tipo**, un **Valor** y **Notas** opcionales.
Cada evento cuenta desde su fecha en adelante.

| Tipo | Efecto sobre el valor |
|---|---|
| **Interés** | Un pago de intereses que recibiste: el valor disminuye en esa cantidad |
| **Ajuste de precio** | Una reducción (negativa) o un aumento (positivo) |

## 🧮 Cómo se calcula el valor {: #how-value-is-calculated }

LibreFolio recorre el calendario día a día. En el día $d$, el valor es

$$
V(d) = V_0 + I(d) - \sum \text{Eventos de interés} + \sum \text{Ajustes de precio}
$$

donde $V_0$ es el **Valor inicial**, $I(d)$ el interés acumulado hasta ahora, y las sumas cubren los
eventos hasta el día $d$. Cada día añade interés a la tasa anual del periodo $r$ durante $\Delta t$, la
parte de un día del año según el **Recuento de días** (por ejemplo, $1/365$ con ACT/365):

- **Simple** — interés solo sobre el valor inicial: $\Delta I = V_0 \, r \, \Delta t$
- **Compuesto** — interés también sobre el interés ya acumulado: $\Delta I = (V_0 + I) \, r \, \Delta t$

Con **Generar cupón**, en cada fecha de vencimiento la ganancia $V(d) - V_0$, cuando es positiva, se paga
como un evento de interés: el valor vuelve a empezar desde $V_0$, y $I$ y las sumas se reinician desde cero.

- **Antes del primer periodo**, el valor es el Valor inicial.
- **Después del último periodo**, se mantiene en su importe final, a menos que el interés de demora esté activado. Con
  **Generar cupón** en el último periodo y sin interés de demora, un evento de liquidación al vencimiento cierra el activo en ese importe.
- **El gráfico** obtiene un punto en cada fecha de **Frecuencia**: elige **Diaria** para una línea suave.

??? example "🧮 Un préstamo de 10.000 € al 5 %, con un cupón cada mes"

    Interés simple, ACT/365, un periodo que comienza el 1 de enero, **Frecuencia** Mensual,
    **Generar cupón** marcado. La primera fecha de vencimiento es el 1 de febrero, 31 días después: el préstamo ha
    generado unos 42,47 € ($10\,000 \times 0.05 \times 31/365$). Esa cantidad se paga como un
    evento de interés, y el valor vuelve a 10.000 € para crecer de nuevo en febrero.

## 🔗 Relacionados

- 📅 **[Eventos del activo](../detail/events.md)** — Cómo se muestran los eventos en el gráfico del activo
- 🛠️ **Para desarrolladores: [Proveedor de inversión programada](../../../developer/backend/assets/provider_scheduled_investment.md)** — Motor, eventos y caché
