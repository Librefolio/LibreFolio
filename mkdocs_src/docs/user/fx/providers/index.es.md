# 🔌 Proveedores de FX

LibreFolio sincroniza automáticamente los tipos de cambio utilizando fuentes oficiales de los bancos centrales. Cada par de divisas que configure puede tener una lista priorizada de fuentes, creando un sistema de fallback robusto en caso de que un servicio deje de funcionar.

<div class="grid cards" style="margin-top: 1.5rem; margin-bottom: 2rem;">
 <a href="ecb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.ecb.europa.eu/favicon-32.png" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon del BCE">
 <span class="card-title" style="margin: 0;">Banco Central Europeo (BCE)</span>
 </div>
 <span class="card-desc">Tipos de cambio de referencia diarios del BCE, moneda base EUR.</span>
 </a>
 <a href="fed/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://fred.stlouisfed.org/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon de la FED">
 <span class="card-title" style="margin: 0;">Reserva Federal (FED)</span>
 </div>
 <span class="card-desc">Tipos de cambio de la base de datos FRED, moneda base USD.</span>
 </a>
 <a href="boe/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon del BOE">
 <span class="card-title" style="margin: 0;">Banco de Inglaterra (BOE)</span>
 </div>
 <span class="card-desc">Tipos de referencia diarios del BOE, moneda base GBP.</span>
 </a>
 <a href="snb/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
 <div style="display: flex; align-items: center; gap: 0.75rem;">
 <img src="https://data.snb.ch/favicon.ico" width="24" height="24" style="object-fit: contain; border-radius: 4px;" alt="favicon del SNB">
 <span class="card-title" style="margin: 0;">Banco Nacional Suizo (SNB)</span>
 </div>
 <span class="card-desc">Tipos de cambio diarios estables del franco suizo del SNB, moneda base CHF.</span>
 </a>
 <a href="../../../community/contribute/" class="card-link" style="flex-direction: column; align-items: stretch; gap: 0.5rem;">
  <div style="display: flex; align-items: center; gap: 0.75rem;">
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: var(--md-accent-fg-color);"><path d="M15.39 4.39a1 1 0 0 0 1.68-.474 2.5 2.5 0 1 1 3.014 3.015 1 1 0 0 0-.474 1.68l1.683 1.682a2.414 2.414 0 0 1 0 3.414L19.61 15.39a1 1 0 0 1-1.68-.474 2.5 2.5 0 1 0-3.014 3.015 1 1 0 0 1 .474 1.68l-1.683 1.682a2.414 2.414 0 0 1-3.414 0L8.61 19.61a1 1 0 0 0-1.68.474 2.5 2.5 0 1 1-3.014-3.015 1 1 0 0 0 .474-1.68l-1.683-1.682a2.414 2.414 0 0 1 0-3.414L4.39 8.61a1 1 0 0 1 1.68.474 2.5 2.5 0 1 0 3.014-3.015 1 1 0 0 1-.474-1.68l1.683-1.682a2.414 2.414 0 0 1 3.414 0z"/></svg>
  <span class="card-title" style="margin: 0;">Solicitar Nuevo Plugin</span>
  </div>
  <span class="card-desc">¿Falta tu proveedor de tasas de cambio? ¡Solicita un nuovo plugin o contribuye!</span>
 </a>
 </div>

## 📊 Comparativa de Proveedores

| <span style="min-width: 320px;">Proveedor</span> | Moneda Base | Divisas Soportadas | <span style="min-width: 220px;">Frecuencia de Actualización</span> | API Key | Notas |
|:---|:---:|:---:|:---:|:---:|:---|
| <img src="https://www.ecb.europa.eu/favicon-32.png" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **ECB** (Banco Central Europeo) | EUR 🇪🇺 | ~45 | Diario, ~16:00 CET | No requerida | Proveedor principal para pares basados en Euro y divisas mundiales importantes. |
| <img src="https://fred.stlouisfed.org/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **FED** (Reserva Federal FRED) | USD 🇺🇸 | ~20 | Diario, días hábiles en EE. UU. | No requerida | Mejor fallback para pares basados en Dólar estadounidense. |
| <img src="https://www.bankofengland.co.uk/favicon.svg?ver=2c06d" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **BOE** (Banco de Inglaterra) | GBP 🇬🇧 | ~15 | Diario, días hábiles en Reino Unido | No requerida | Buena cobertura para pares basados en Libra esterlina. |
| <img src="https://data.snb.ch/favicon.ico" width="16" height="16" style="vertical-align: middle; margin-right: 6px; border-radius: 2px;"> **SNB** (Banco Nacional Suizo) | CHF 🇨🇭 | ~10 | Diario, días hábiles en Suiza | No requerida | Cotizaciones muy estables para pares de Franco suizo. |

## 🎯 Cómo funcionan el Enrutamiento y el Fallback

LibreFolio no te limita a una única fuente. Al gestionar los tipos de cambio:

1. 🛤️ **Rutas Directas**: Si existe un tipo de cambio directo (p. ej., EUR/USD a través del ECB), LibreFolio lo obtiene.
2. 🔀 **Rutas en Cadena**: Si ningún proveedor directo soporta tu par (p. ej., EUR/RON), LibreFolio puede convertirlo a través de una cadena (p. ej., EUR → USD → RON) automáticamente.
3. 🔄 **Fallback Automático**: Si tu proveedor principal falla durante la sincronización (p. ej., tiempo de espera de red agotado), LibreFolio intenta automáticamente el siguiente proveedor configurado.
4. ✍️ **Sentinel Manual**: Para pares de divisas que no están soportados por ningún banco central, puedes establecer el proveedor como `MANUAL` para introducir los tipos tú mismo.
