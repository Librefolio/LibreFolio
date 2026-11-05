# <img src="https://traderepublic.com/favicon.ico" alt=""> Trade Republic

!!! warning "Beta — se agradecen los comentarios de la comunidad"

    Este plugin se creó a partir de **archivos de exportación de ejemplo** y actualmente está en **beta**. Agradecemos cualquier informe para mejorarlo o para actualizar la documentación sobre cómo obtener el archivo de exportación.

## 📥 Cómo exportar

Exporta tu historial de transacciones como **CSV** desde Trade Republic y súbelo en LibreFolio. Para ver el proceso de importación paso a paso, consulta la **[Guía de importación](how-to.md)**.

## 📝 Notas

- Creado a partir de exportaciones de ejemplo — puede que algunos casos límite aún no estén cubiertos.
- **Las columnas de comisión e impuesto (*Kosten*, *Belasting*) todavía no se importan**: la fila en sí se importa, y un aviso en ámbar enumera las filas que tienen una comisión o un impuesto, con un enlace para abrir una incidencia en GitHub. Añade la comisión o el impuesto a mano. Ese mismo aviso enumera las filas que LibreFolio no conoce o no puede leer.
- **¿No estás seguro de que el valor neto sea realmente neto?**: consulta [Comprobar el importe neto](#check-the-net-amount) más abajo.
- ¿Has encontrado un problema o quieres documentar los pasos de exportación? [Abre un informe](../../../community/contribute.md) — ¡las contribuciones son bienvenidas!

## 🔍 Comprobar el importe neto {: #check-the-net-amount }

!!! warning "No sabemos si el valor neto ya incluye la comisión y el impuesto"

    LibreFolio importa cada compra o venta tomando como efectivo el valor de la columna **`Waarde (netto)`** («valor neto»).
    **No sabemos** si ese valor ya contiene la comisión (**`Kosten`**) y el impuesto
    (**`Belasting`**) de la fila: el desarrollador no dispone de una exportación reciente y segura de
    Trade Republic con la que comprobarlo.

    Un ejemplo sencillo: compras acciones y Trade Republic te cobra una comisión de 1.00 EUR.

    - **Si el valor neto ya incluye la comisión** (por ejemplo, 101.00 EUR, de los cuales 1.00 es la comisión),
      la compra ya es correcta. Añadir la comisión de 1.00 EUR a mano, como sugiere el aviso en ámbar, haría
      que la comisión se contara **dos veces**.
    - **Si el valor neto no incluye la comisión** (muestra 100.00 EUR), el efectivo de la compra
      es 1.00 EUR inferior al real, y hay que añadir la comisión a mano.

    El mismo razonamiento se aplica a una venta y al impuesto.

**Qué comprobar antes de añadir nada:**

1. Elige una compra o una venta que tenga una comisión o un impuesto (el aviso en ámbar enumera esas filas).
2. Compárala con tu **extracto de cuenta** o con el total que muestra la app de Trade Republic:
   ¿coincide el efectivo que salió de tu cuenta (o entró en ella, en el caso de una venta) con lo que
   LibreFolio muestra para esa fila?
3. Si ambos importes **coinciden**, la comisión ya está incluida: **no** la añadas. Si LibreFolio muestra **menos**
   que el movimiento real de efectivo, añade **Kosten** y **Belasting** a mano como transacciones
   independientes de tipo comisión e impuesto.

Un archivo real, **de ejemplo y anonimizado**, resolvería la cuestión de una vez por todas. Si puedes compartir uno,
[abre una incidencia](https://github.com/Librefolio/LibreFolio/issues): así corregiremos el importador y
esta página.
