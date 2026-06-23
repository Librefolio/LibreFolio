# <img src="../../../../../static/scheduled_investment.png" alt=""> Scheduled Investment Provider

Il provider Scheduled Investment è progettato per strumenti a reddito fisso in cui il valore è calcolato in base a un piano di tassi di interesse piuttosto che ai prezzi di mercato. Esempi includono conti di risparmio, depositi vincolati e titoli di stato con tassi di cedola noti.

## 📊 Capacità

- ✅ **Prezzo Corrente**: Calcolato deterministicamente da valore iniziale + piano di interessi + eventi dell'asset
- ✅ **Cronologia**: Curva del valore storico completa basata sull'accumulo di interessi
- ✅ **Eventi dell'Asset**: Genera eventi INTEREST e PRICE_ADJUSTMENT
- ❌ **Ricerca**: Non applicabile

## 🔧 Configurazione

- **Identificatore**: Generato automaticamente (non è necessario un identificatore manuale)
- **Tipo di Identificatore**: `AUTO_GENERATED`
- **Parametri**: Configurati tramite l'**Interest Schedule Editor** (componente UI personalizzato)

### Campi Obbligatori

| Campo | Descrizione |
|-------|-------------|
| **Initial Value** | Il capitale / valore nominale dell'investimento (es. 10000) |
| **Currency** | Codice valuta ISO 4217 (es. EUR, USD) |

## 📋 Interest Schedule Editor

L'editor consente di definire molteplici periodi di tasso di interesse:

| Campo | Descrizione |
|-------|-------------|
| **Period** | Data di inizio e fine (entrambe inclusive) |
| **Rate %** | Tasso di interesse annuo in percentuale (es. 5.00 = 5%) |
| **Compounding** | Interesse semplice o composto |
| **Comp. Freq.** | Frequenza di capitalizzazione (Annuale, Semestrale, Trimestrale, Mensile, Giornaliera) |
| **Day Count** | Convenzione di conteggio dei giorni (ACT/365, ACT/360, 30/360, ACT/ACT) |

### ⚡ Late Interest

È possibile abilitare il **Late Interest** per definire un tasso di penale applicato dopo la fine dell'ultimo periodo programmato. Il Late Interest ha un **periodo di grazia** configurabile (in giorni) prima che inizino a maturare gli interessi di mora.

## 📋 Asset Events

Gli eventi dell'asset descrivono quanto accade all'asset a livello globale (non transazioni a livello di portafoglio):

| Tipo di Evento | Effetto sul Prezzo | Descrizione |
|-----------|----------------|-------------|
| **INTEREST** | Il prezzo scende del valore dell'evento | Pagamento interessi — l'utente ha ricevuto contanti, quindi il valore dell'asset diminuisce |
| **PRICE_ADJUSTMENT** | Modifica algebrica | Svalutazione (negativa) o rivalutazione (positiva) del valore dell'asset |

Gli eventi sono configurati nell'editor e influenzano il prezzo calcolato a partire dalla loro data.

## 🧮 Come viene calcolato il valore

1. Si parte da `initial_value` come capitale di base
2. Per ogni periodo di interesse, si calcola l'interesse maturato in base al tasso, al tipo di capitalizzazione e alla convenzione di conteggio dei giorni
3. Si applicano gli eventi dell'asset: gli eventi INTEREST riducono il prezzo, gli eventi PRICE_ADJUSTMENT lo modificano algebricamente
4. Il valore corrente = `initial_value` + interessi maturati - Σ(eventi INTEREST) + Σ(eventi PRICE_ADJUSTMENT)

!!! note "Motore Puramente Deterministico"

    Il provider è completamente deterministico — a parità di configurazione, produce sempre gli stessi prezzi. NON accede al database né legge le transazioni. Tutti gli input provengono da `provider_params`.

## 🎯 Casi d'Uso

- **Conti di risparmio** con tassi di interesse fissi o variabili
- **Depositi a termine** (CD/Depositi vincolati)
- **Titoli di stato** dove si desidera monitorare l'interesse maturato piuttosto che il prezzo di mercato
- **Prestiti in crowdfunding** (P2P lending) con piani di interessi noti
- **Qualsiasi strumento** con un piano di tassi di interesse noto
