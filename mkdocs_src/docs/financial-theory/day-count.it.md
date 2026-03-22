# 📅 Convenzioni sul Conteggio dei Giorni

Una **Convenzione sul Conteggio dei Giorni** determina come gli interessi maturano nel tempo per vari strumenti finanziari, come obbligazioni, prestiti e mutui. Definisce due elementi:

1. Come calcolare il numero di giorni tra due date.
2. Come calcolare il numero di giorni in un anno.

## 🔧 Utilizzo in LibreFolio

Le convenzioni sul conteggio dei giorni vengono utilizzate dal modulo **Scheduled Investment** 
(`backend/app/services/asset_source_providers/scheduled_investment.py`) per 
il calcolo del rendimento sintetico. La funzione `calculate_day_count_fraction()` in 
`backend/app/utils/financial_math.py` implementa tutte e quattro le convenzioni e restituisce una 
**frazione temporale** `Decimal` utilizzata nei calcoli di maturazione degli interessi.

La convenzione predefinita è **ACT/365**.

## 📅 ACT/365 (Actual/365)

- **Giorni**: Il numero effettivo di giorni tra due date.
- **Anno**: Assunto di 365 giorni.
- **Formula**: $t = \frac{\text{giorni effettivi}}{365}$
- **Utilizzo**: Comune nei mercati monetari britannici e per alcuni titoli di Stato. **Predefinita in LibreFolio.**

## 📅 ACT/360 (Actual/360)

- **Giorni**: Il numero effettivo di giorni tra due date.
- **Anno**: Assunto di 360 giorni.
- **Formula**: $t = \frac{\text{giorni effettivi}}{360}$
- **Utilizzo**: Molto comune nei mercati monetari statunitensi e per prestiti commerciali.

## 📐 30/360 (Bond Basis)

- **Giorni**: Calcolati assumendo che ogni mese abbia 30 giorni.
- **Anno**: Assunto di 360 giorni.
- **Formula**: $t = \frac{360(Y_2 - Y_1) + 30(M_2 - M_1) + (D_2 - D_1)}{360}$
- **Utilizzo**: Standard per le obbligazioni societarie statunitensi e molte obbligazioni municipali.

## 📅 ACT/ACT (Actual/Actual)

- **Giorni**: Il numero effettivo di giorni tra due date.
- **Anno**: Il numero effettivo di giorni nell'anno (365 o 366 negli anni bisestili).
- **Formula**: $t = \frac{\text{giorni effettivi}}{365 \text{ o } 366}$
- **Utilizzo**: Standard per le **obbligazioni del Tesoro USA**. Gestisce correttamente gli anni bisestili calcolando la frazione per ciascun anno separatamente.

!!! info "Perché questo è importante?"
    La differenza tra le convenzioni può essere significativa per capitali elevati o durate 
    lunghe. Ad esempio, 30 giorni su un prestito di €1.000.000 al 5%: ACT/365 dà €4.109,59 di 
    interessi, mentre ACT/360 dà €4.166,67 — una differenza di €57 dallo stesso periodo di 30 giorni.

:material-link: [Convenzione sul Conteggio dei Giorni su Wikipedia](https://en.wikipedia.org/wiki/Day_count_convention){ target="_blank" }

[^4]: **Nota del traduttore**: La variante ACT/ACT descritta è quella standard per i Treasury bond USA. Esiste anche la variante ICMA (usata in Europa) che tratta diversamente i periodi che attraversano anni bisestili. Qui "obbligazioni del Tesoro USA" è la traduzione corretta per *US Treasury bonds* (non "buoni", che sono T-bills a breve termine). La formula gestisce gli anni bisestili suddividendo il calcolo per anno solare.
