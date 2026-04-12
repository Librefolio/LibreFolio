# 📅 Convenzioni di Calcolo dei Giorni (Day Count Conventions)

Una **Convenzione di Calcolo dei Giorni** (Day Count Convention) determina come gli interessi maturino nel tempo per una varietà di strumenti finanziari, come obbligazioni, prestiti e mutui. Definisce due aspetti:

1. Come calcolare il numero di giorni tra due date.
2. Come calcolare il numero di giorni in un anno.

## 🔧 Utilizzo in LibreFolio

Le convenzioni di calcolo dei giorni sono attivamente utilizzate dal provider della sorgente degli asset **Scheduled Investment** (`backend/app/services/asset_source_providers/scheduled_investment.py`) per i calcoli dei rendimenti sintetici. La funzione `calculate_day_count_fraction()` in `backend/app/utils/financial_math.py` implementa tutte e quattro le convenzioni e restituisce una frazione temporale `Decimal` utilizzata nei calcoli di maturazione degli interessi.

La convenzione predefinita è **ACT/365**.

## 📅 ACT/365 (Actual/365)

- **Giorni**: Il numero effettivo di giorni tra due date.
- **Anno**: Si assume che l'anno sia di 365 giorni.
- **Formula**: $t = \frac{\text{giorni effettivi}}{365}$
- **Utilizzo**: Comune nei mercati monetari del Regno Unito e per alcuni titoli di stato. **Predefinita in LibreFolio.**

## 📅 ACT/360 (Actual/360)

- **Giorni**: Il numero effettivo di giorni tra due date.
- **Anno**: Si assume che l'anno sia di 360 giorni.
- **Formula**: $t = \frac{\text{giorni effettivi}}{360}$
- **Utilizzo**: Molto comune nei mercati monetari degli Stati Uniti e per i prestiti commerciali.

## 📐 30/360 (Bond Basis)

- **Giorni**: Calcolati assumendo che ogni mese abbia 30 giorni.
- **Anno**: Si assume che l'anno sia di 360 giorni.
- **Formula**: $t = \frac{360(Y_2 - Y_1) + 30(M_2 - M_1) + (D_2 - D_1)}{360}$
- **Utilizzo**: Standard per le obbligazioni societarie statunitensi e molte obbligazioni municipali.

## 📅 ACT/ACT (Actual/Actual)

- **Giorni**: Il numero effettivo di giorni tra due date.
- **Anno**: Il numero effettivo di giorni nell'anno (365 o 366 per gli anni bisestili).
- **Formula**: $t = \frac{\text{giorni effettivi}}{365 \text{ o } 366}$
- **Utilizzo**: Standard per i titoli del Tesoro degli Stati Uniti. Gestisce correttamente gli anni bisestili calcolando la frazione per ogni anno separatamente.

!!! info "Perché questo è importante?"

    La differenza tra le convenzioni può essere significativa per capitali elevati o durate lunghe. Ad esempio, 30 giorni su un prestito di 1 mln € al 5%: ACT/365 produce 4.109,59 € di interessi, mentre ACT/360 produce 4.166,67 € — una differenza di 57 € per lo stesso periodo di 30 giorni.

:material-link: [Day Count Convention su Wikipedia](https://en.wikipedia.org/wiki/Day_count_convention){ target="_blank" }
