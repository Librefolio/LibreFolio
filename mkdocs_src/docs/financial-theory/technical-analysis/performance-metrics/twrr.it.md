# ⏱️ TWRR (Time-Weighted Rate of Return)

*[⬅️ Torna a Panoramica sulle metriche di performance](index.md)*

## 💡 Cos'è?
Il TWRR misura la performance "pura" degli asset scelti (il Mercato), ignorando completamente il momento e l'entità dei tuoi depositi o prelievi.

## 🧮 Come funziona
Ogni volta che depositi o prelevi denaro, il TWRR "divide" la timeline in un sotto-periodo. Calcola il rendimento per quel sotto-periodo specifico e poi collega (moltiplica) tra loro tutti i sotto-periodi. 

$$
R_{TWRR} = \prod_{i=1}^{n} (1 + r_i) - 1
$$

## 🎯 Quando usarlo
- Per valutare se gli **asset che hai scelto** siano effettivamente performanti.
- Per confrontare il tuo portafoglio con un benchmark esterno (come l'S&P 500).
- I fondi comuni e gli ETF riportano sempre il TWRR, poiché il gestore del fondo non può controllare quando i clienti depositano o prelevano denaro.
