# <img src="https://www.swissquote.com/favicon.ico" alt=""> Swissquote

!!! warning "Beta — se agradecen los comentarios de la comunidad"

    Este complemento se creó a partir de **archivos de exportación de muestra** y actualmente está en **beta**. Agradecemos cualquier informe para mejorarlo o para actualizar la documentación sobre cómo obtener la exportación.

## 📥 Cómo exportar

Exporta tu historial de transacciones como **CSV** desde Swissquote y súbelo a LibreFolio. Para ver el flujo de importación paso a paso, consulta la **[Guía de importación](how-to.md)**.

## 🔄 Qué se importa

| En la exportación (**Transacción**) | Se importa como |
|:--------------------------------|:------------|
| Compra | **Compra** |
| Venta | **Venta** |
| Dividendo | **Dividendo** |
| Interés, intereses | **Interés** |
| Impuesto, retención | **Impuesto** |
| Comisión de custodia, cualquier otra comisión | **Comisión** |
| Débito | **Retiro** |
| Crédito | **Depósito** |
| Crédito Forex + débito Forex, mismo **Order #** | Un par vinculado de **cambio de divisas** |

**Conversiones de divisa.** Las dos patas de una conversión, un **crédito Forex** y un **débito Forex**
con el mismo **Order #**, se convierten en dos transacciones de **cambio de divisas** vinculadas: el dinero que sale en una
moneda y el dinero que entra en la otra. Cada pata conserva su propia fecha y su propio **importe neto**.

## 📝 Notas

- Creado a partir de exportaciones de muestra — es posible que algunos casos límite aún no estén cubiertos.
- Los costes y los intereses devengados de una operación se escriben en su descripción; no se importan como transacciones separadas.
- Las filas que LibreFolio no reconoce se enumeran en un aviso ámbar, con un enlace para abrir una incidencia en GitHub; un segundo aviso enumera las filas que no puede leer.
- ¿Has encontrado algún problema o quieres documentar los pasos de exportación? [Abre un informe](../../../community/contribute.md) — ¡se agradecen las contribuciones!

## 🚧 Limitaciones conocidas

- **Solo se importa un par limpio de patas de Forex.** Una pata de Forex se deja fuera y se enumera en el aviso ámbar con el enlace para abrir una incidencia (añade esa conversión a mano) cuando:
    - falta su pareja (no hay otra pata con el mismo **Order #**);
    - la orden tiene más de dos patas;
    - una pata incluye **Costes** (el archivo no indica si el coste está dentro o fuera de su **importe neto**);
    - las dos patas están en la misma moneda, o ambas son créditos o ambas son débitos.
- **¿Algo no cuadra?** Por favor, [abre un informe](../../../community/contribute.md) con un archivo de ejemplo anonimizado.
