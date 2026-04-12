# ✂️ Split

Un **split** (o split inverso) es una acción corporativa que cambia el número de acciones en circulación manteniendo constante la capitalización de mercado total.

---

## 📖 Definición

En un split, una empresa divide sus acciones existentes en múltiples acciones nuevas. El **valor total** de la posición de un inversor permanece igual; solo cambian el número de acciones y el precio por acción.

### Split Forward

La empresa aumenta el número de acciones. Cada acción existente se convierte en múltiples acciones a un precio proporcionalmente menor.

| Ratio | Significado |
|-------|---------|
| **2:1** | Cada acción se convierte en 2 acciones a la mitad del precio |
| **3:1** | Cada acción se convierte en 3 acciones a un tercio del precio |
| **4:1** | Cada acción se convierte en 4 acciones a un cuarto del precio |
| **10:1** | Cada acción se convierte en 10 acciones a un décimo del precio |

### Reverse Split

La empresa reduce el número de acciones. Múltiples acciones existentes se fusionan en menos acciones a un precio proporcionalmente mayor.

| Ratio | Significado |
|-------|---------|
| **1:2** | Cada 2 acciones se convierten en 1 acción al doble del precio |
| **1:10** | Cada 10 acciones se convierten en 1 acción a 10x el precio |
| **1:20** | Cada 20 acciones se convierten en 1 acción a 20x el precio |

---

## 📉 Impacto en el Precio de Mercado

Un split provoca un **cambio de precio inmediato y proporcional** que es matemáticamente neutro:

$$
P_{\text{after}} = \frac{P_{\text{before}}}{\text{split ratio}}
$$

$$
Q_{\text{after}} = Q_{\text{before}} \times \text{split ratio}
$$

Donde $P$ es el precio por acción y $Q$ es la cantidad de acciones.

!!! example "Ejemplo: Split 4:1 de Apple (Agosto 2020)"

    - **Antes del split**: 100 acciones × $500 = $50,000 valor total
    - **Después del split**: 400 acciones × $125 = $50,000 valor total
    - **Cambio de precio**: −75% (pero el valor de la posición no cambia)

!!! example "Ejemplo: Reverse Split 1:10"

    - **Antes**: 1,000 acciones × $0.50 = $500 valor total
    - **Después**: 100 acciones × $5.00 = $500 valor total
    - **Razón**: La empresa desea subir el precio de la acción por encima de los requisitos mínimos de cotización de la bolsa

---

## 📊 Por qué las empresas hacen Splits

### Split Forward

- **Accesibilidad**: Un precio por acción más bajo hace que la acción sea más accesible para los inversores minoristas
- **Liquidez**: Un mayor número de acciones en circulación puede aumentar el volumen de negociación
- **Psicología**: Un precio nominal más bajo puede atraer a más compradores
- **Opciones**: Un precio por acción más bajo reduce el capital necesario para los contratos de opciones (100 acciones por contrato)

### Reverse Split

- **Cumplimiento de cotización**: Las bolsas requieren precios mínimos de las acciones (por ejemplo, $1.00 en NASDAQ)
- **Percepción institucional**: Algunos fondos tienen requisitos de precio mínimo
- **A menudo una señal de advertencia**: Los Reverse Split suelen asociarse con empresas en dificultades

---

## 📈 Ajuste de Precios Históricos

Al analizar los precios históricos a través de los splits, los proveedores de datos suelen proporcionar **precios ajustados**: todos los precios históricos se dividen por el ratio de split acumulado para que el gráfico muestre una línea suave.

Por ejemplo, si Apple costaba $100 antes de un split 4:1, el precio histórico ajustado se convierte en $25 para coincidir con la escala posterior al split.

---

## 🧮 Cómo gestiona LibreFolio los Splits

En LibreFolio, un evento `SPLIT` se registra con:

- **Date**: La fecha efectiva del split
- **Amount**: El ratio del split (por ejemplo, `2` para un split 2:1, `0.1` para un reverse split 1:10)
- **Notes**: Descripción opcional (por ejemplo, "split forward 4:1")

Los eventos de split aparecen como **marcadores en el gráfico** y ayudan a explicar discontinuidades repentinas de precio. Cuando se utilizan **precios ajustados** de proveedores como Yahoo Finance, el split ya está factorizado en los datos de precios.

---

## 🔗 Relacionado

- 📅 **[Descripción general de eventos de activos](index.md)** — Todos los tipos de eventos
- 💸 **[Tipos de Transacciones](../transaction-types/index.md)** — Cómo afectan los splits a las transacciones de la cartera
- 📚 **[Tipos de Activos](../asset-types/index.md)** — Tipos de activos que pueden sufrir splits
