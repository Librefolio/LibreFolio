# <img src="https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico" alt=""> Investimental

!!! warning "Beta — comentarios bienvenidos"

    Este plugin se ha escrito a partir de los **archivos de ejemplo** y actualmente está en **beta**. Estaremos encantados de recibir cualquier informe para mejorarlo o para actualizar la documentación sobre cómo obtener la exportación.

## 📥 Cómo Exportar

Exporta tu historial de transacciones en formato **CSV** desde Investimental e impórtalo en LibreFolio. Para el proceso guiado paso a paso, consulta la **[Guía de Importación](how-to.md)**.

## 📝 Notas

- Escrito a partir de los archivos de ejemplo — puede que algunos casos límite aún no estén cubiertos.
- Una orden ejecutada en varias partes se convierte en **una** transacción con toda la cantidad y todo el importe ejecutados, con la fecha de su última ejecución; un aviso te lo dice cuando las partes caen en días distintos o sus cifras no cuadran. Importada con una versión anterior, una orden así conservaba solo su última parte: borra esa transacción e importa de nuevo el archivo.
- Una exportación que empieza con una orden ya en curso (sin sus primeras filas) no puede dar la cantidad total de esa orden: la orden se deja fuera, y un aviso muestra lo que tiene el archivo (fecha, precio, la parte que muestra) para que la introduzcas a mano con tu extracto.
- ¿Has encontrado un problema o quieres documentar los pasos de exportación? [Abre un informe](../../../community/contribute.md) — ¡las contribuciones son bienvenidas!
