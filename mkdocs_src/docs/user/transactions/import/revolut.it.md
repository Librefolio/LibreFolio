# <img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" alt=""> Revolut

!!! info "Beta"

    Questo plugin è in **Beta** — testato con file di esempio, ma potrebbero esserci casi limite.

## 📥 Come Esportare

Per esportare la cronologia delle transazioni di azioni/crypto da Revolut:

1. Apri l'**app mobile di Revolut** o accedi tramite il client web.
2. Naviga nella scheda **Invest** (o Azioni/Crypto).
3. Tocca **... (Altro)** accanto al saldo del tuo portafoglio, quindi seleziona **Estratti conto**.
4. Seleziona il conto desiderato (es. conto Azioni) e tocca **Estratto conto transazioni**.
5. Imposta l'intervallo di tempo, scegli **CSV** come formato ed esporta. Trasferisci il file sul tuo computer.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Revolut App - Invest Statements selection and CSV export] -->
</div>

## ⚠️ Insidie Comuni

!!! warning "Conto di Trading vs Conto Principale"

    Assicurati di esportare l'estratto conto dal sottoconto **Invest/Trading**. L'estratto conto della carta di debito principale di Revolut utilizza un formato di file completamente diverso e non può essere analizzato da questo plugin.

## 📝 Note

- Supporta transazioni di azioni, acquisti di crypto, dividendi pagati, commissioni di custodia e trasferimenti di denaro.
- Gestisce automaticamente importi in più valute nello stesso file.

## 🔗 Riferimento per Sviluppatori

→ [Revolut Provider — Dettagli di Implementazione](../../../developer/backend/brim/providers_list.md)
