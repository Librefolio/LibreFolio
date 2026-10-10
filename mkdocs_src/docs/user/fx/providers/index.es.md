# 🔌 Proveedores FX

LibreFolio descarga los tipos de cambio de los bancos centrales — gratis y sin necesidad de una
clave de API. Un par de divisas puede tener varias fuentes ordenadas por prioridad: si la primera
falla durante una sincronización, la siguiente toma el relevo.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
    <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon del BCE">
            <span class="card-title" style="margin: 0;">Banco Central Europeo (BCE)</span>
        </div>
        <span class="card-desc">Tipos de cambio de referencia diarios del BCE, divisa base EUR.</span>
    </a>
    <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon de la FED">
            <span class="card-title" style="margin: 0;">Reserva Federal (FED)</span>
        </div>
        <span class="card-desc">Tipos de cambio de la base de datos FRED, divisa base USD.</span>
    </a>
    <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon del BOE">
            <span class="card-title" style="margin: 0;">Banco de Inglaterra (BOE)</span>
        </div>
        <span class="card-desc">Tipos de referencia diarios del BOE, divisa base GBP.</span>
    </a>
    <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
            <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="Favicon del BNS">
            <span class="card-title" style="margin: 0;">Banco Nacional Suizo (SNB)</span>
        </div>
        <span class="card-desc">Tipos de cambio del franco suizo con media mensual estable del SNB, divisa base CHF.</span>
    </a>
    <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
     <div style="display: flex; align-items: center; gap: 0.75rem;">
     <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
     <span class="card-title" style="margin: 0;">Solicitar nuevo plugin</span>
     </div>
     <span class="card-desc">¿Falta tu fuente de tipos de cambio? ¡Solicita un nuevo plugin o contribuye con código!</span>
    </a>
    </div>

## 📊 Comparación de proveedores

Cada banco central cotiza otras divisas frente a la suya propia, la **divisa base**.

| <span style="min-width: 320px;">Proveedor</span> | Divisa base | <span style="min-width: 220px;">Frecuencia de actualización</span> | Adecuado para |
|:---|:---:|:---|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BCE** (Banco Central Europeo) | EUR 🇪🇺 | Diaria, hacia las 16:00 CET en días hábiles del BCE | Pares del euro y las principales divisas mundiales |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Reserva Federal FRED) | USD 🇺🇸 | Diaria, en días hábiles de EE. UU. | Pares del dólar estadounidense |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Banco de Inglaterra) | GBP 🇬🇧 | Diaria, en días hábiles del Reino Unido | Pares de la libra esterlina |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Banco Nacional Suizo) | CHF 🇨🇭 | Medias mensuales, un valor por mes | Pares del franco suizo, cuando basta con un tipo mensual |

## 🎯 Cómo funcionan el enrutamiento y el fallback

1. 🛤️ **Ruta directa**: un banco central cotiza el par — por ejemplo, EUR/USD del BCE.
2. 🔀 **Ruta encadenada**: ningún banco cotiza el par, así que LibreFolio combina pasos — por
   ejemplo, RON/USD como RON → EUR → USD, ambos pasos del BCE. Una cadena obtiene un tipo solo
   los días en que todos los pasos tienen uno.
3. 🔄 **Fallback**: cuando hay varias rutas, una sincronización las prueba por orden de prioridad
   y usa la primera que funciona.
4. ✍️ **Manual**: ¿no hay ruta para tu par? Guárdalo sin proveedor e introduce los tipos tú mismo
   en el [Editor de datos](../detail/data-editor.md).

Eliges las rutas cuando [añades un par](../add-pair.md) y las cambias después con el botón
[Proveedores](../detail/provider.md) del par.

!!! warning "SNB: un tipo por mes"

    El SNB publica medias mensuales, con fecha del día 1 de cada mes. Un par que lo use obtiene un
    tipo por mes, y una cadena que pase por el SNB tiene tipos solo en esos días.

## 🔗 Relacionado

- 🛠️ **Para desarrolladores: [Proveedores FX](../../../developer/backend/fx/providers/index.md)** — APIs, series y formatos de cotización
