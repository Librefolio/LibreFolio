# <img src="https://www.finpension.ch/favicon.ico" alt=""> Finpension

!!! info "Beta"

    Este plugin está en **Beta**: se ha probado con archivos de muestra, pero podrían existir casos aislados.

## 📥 Cómo exportar

Para exportar sus transacciones desde Finpension:

1. Inicie sesión en su [cuenta de Finpension](https://app.finpension.ch).
2. Vaya al panel de control de su cartera o cuenta activa.
3. Haga clic en la pestaña **Transactions** (Transazioni / Transaktionen).
4. Haga clic en el botón **Export** o de descarga y seleccione **CSV**.
5. Guarde el archivo en su ordenador.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Finpension Portal - Transactions page and Export button] -->
</div>

## ⚠️ Errores comunes

!!! warning "No modifique los delimitadores"

    Las exportaciones de Finpension utilizan el punto y coma `;` como separador de columnas y formatos alemanes/suizos. El analizador BRIM detecta estas configuraciones regionales automáticamente. Evite abrir el archivo en editores de hojas de cálculo (como Excel) y volver a guardarlo, ya que esto podría alterar la estructura bruta del CSV.

## 📝 Notas

- Plataforma de pensiones suiza.
- Admite depósitos en efectivo, compras, ventas, retenciones fiscales y comisiones de gestión.
- Denominado en CHF.

## 🔗 Referencia para desarrolladores

→ [Proveedor Finpension — Detalles de implementación](../../../developer/backend/brim/providers_list.md)
