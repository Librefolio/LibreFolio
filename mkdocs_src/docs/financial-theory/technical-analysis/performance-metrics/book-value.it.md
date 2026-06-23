# 📖 Book Value

*[⬅️ Torna alla Panoramica delle Metriche di Performance](index.md)*

## 💡 Cos'è il Book Value?

In LibreFolio, il **Book Value** rappresenta il costo contabile storico (cost basis) del tuo portafoglio. Riflette l'importo netto di capitale che hai effettivamente impegnato nelle tue posizioni ancora aperte, più la liquidità.

Risponde alla domanda: _"Quanto è costato costruire il mio portafoglio attuale?"_

A differenza del Net Asset Value (NAV), che fluttua con i prezzi di mercato giornalieri, il Book Value cambia solo quando acquisti o vendi asset, o quando la liquidità viene depositata/prelevata. Non rappresenta il valore di liquidazione corrente sul mercato.

---

## 🧮 Formula

Il Book Value è calcolato utilizzando la seguente formula:

$$
\text{Book Value} = \text{Costo Posizioni Aperte} + \text{Liquidità} + \text{Costo in Transito}
$$

Dove:

- **$\text{Costo Posizioni Aperte}$**: Il costo base totale delle tue posizioni ancora aperte, calcolato moltiplicando la quantità di ciascun asset per il relativo [Prezzo Medio di Carico (PMC)](weighted-average-cost.md).
- **$\text{Liquidità}$**: Il saldo di liquidità reale depositato sui conti dei broker inclusi nello scope.
- **$\text{Costo in Transito}$**: Il costo contabile della liquidità o degli asset attualmente in fase di trasferimento tra i conti interni compresi nello scope. Questo concetto è introdotto per gestire quei trasferimenti (es. bonifici o trasferimenti titoli) che a livello contabile partono il giorno 1 da un conto di origine e arrivano il giorno 5 sul conto di destinazione a causa dei tempi tecnici di esecuzione.

---

## 📝 Esempio Pratico

Consideriamo un portafoglio con i seguenti dati:

- **Costo Posizioni Aperte (Costo di Acquisto)**: €27.000
- **Liquidità**: €600
- **Asset in Transito (Costo Contabile)**: €0

Il Book Value è calcolato come:

$$
\text{Book Value} = 27.000 + 600 + 0 = \text{€}27.600
$$

### 📊 Confronto con il NAV (Performance Latente)

Se il valore di mercato attuale ([NAV](nav.md)) di questo portafoglio è **€33.000**, possiamo calcolare la **Plusvalenza/Minusvalenza Latente** (unrealized gain/loss) confrontandolo con il Book Value:

$$
\text{Performance Latente} = \text{NAV} - \text{Book Value}
$$

$$
\text{Performance Latente} = 33.000 - 27.600 = +\text{€}5.400
$$

Ciò indica che il valore di mercato del tuo portafoglio è cresciuto di €5.400 rispetto al prezzo totale pagato per acquistarlo.

---

## ⚙️ Nota sui Metodi del Prezzo di Carico

Per determinare il costo contabile delle posizioni aperte, LibreFolio utilizza il metodo del [Prezzo Medio di Carico (PMC)](weighted-average-cost.md) come algoritmo predefinito di tracciamento dell'inventario:

- Ogni volta che acquisti un asset, viene aggiornato il costo medio unitario di carico.
- Ogni volta che vendi un asset, il costo base totale viene ridotto proporzionalmente in base al PMC al momento della vendita, lasciando invariato il costo unitario delle quote rimanenti.
