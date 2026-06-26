# <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="currentColor" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6m1.8 18H14v-2h1.8v2m0-3H14v-2h1.8v2m0-3H14V9.8h1.8v4.2M13 9V3.5L18.5 9H13M6 20V4h5v7h7v9H6z"/></svg> CSV Générique

Le fournisseur **CSV Générique** est un fallback flexible pour les courtiers qui ne sont pas directement pris en charge. Il permet une correspondance manuelle des colonnes afin que vous puissiez importer depuis n'importe quel export basé sur un fichier CSV.

## Quand l'utiliser

- Votre courtier ne figure pas dans la liste des courtiers pris en charge.
- Un courtier pris en charge a modifié son format d'exportation et le plugin n'a pas encore été mis à jour.
- Vous possédez un tableur personnalisé ou un CSV généré par script que vous souhaitez importer.

## Comment ça marche

1. Téléversez votre fichier CSV.
2. LibreFolio affiche les colonnes brutes détectées.
3. Associez chaque colonne au champ LibreFolio correspondant (date, type, actif, quantité, montant, devise, description).
4. Prévisualisez les lignes analysées et confirmez l'importation.

---

## 🔄 Convertir un rapport personnalisé

Si votre source de données n'est pas prise en charge nativement, vous pouvez écrire un script de conversion pour la transformer au format CSV Générique.

!!! info "Spécifications techniques pour développeurs et LLM"

    La spécification complète du format — notamment les conventions de signe, quand utiliser chaque type de transaction, les patterns P2P, la gestion des annulations et des exemples pratiques — se trouve dans la documentation technique :

    **[CSV Générique — Spécification Technique](../../../developer/backend/brim/generic_csv.md)**

    Vous pouvez coller cette page directement dans un LLM (ChatGPT, Claude, Gemini…) avec quelques lignes d'exemple de votre fichier source, et lui demander d'écrire un script Python de conversion.

---

## 📋 Référence des colonnes

Voici les colonnes reconnues par LibreFolio dans un fichier CSV Générique. Les noms de colonnes ne sont pas sensibles à la casse.

| Colonne | Obligatoire ? | Alias acceptés | Description |
|---------|--------------|----------------|-------------|
| **`date`** | ✅ Toujours | `data`, `settlement_date`, `value_date`, `trade_date`, `fecha`, `datum`, `transaction_date`, `exec_date` | Date de la transaction |
| **`type`** | ✅ Toujours | `tipo`, `transaction_type`, `operation`, `operazione`, `action`, `azione`, `trans_type`, `op_type` | Type de transaction — voir valeurs ci-dessous |
| **`quantity`** | Requis pour BUY/SELL/TRANSFER/ADJUSTMENT | `quantità`, `qty`, `shares`, `azioni`, `units`, `unità`, `amount_shares`, `num_shares` | Nombre d'unités. **Négatif pour SELL, positif pour BUY.** |
| **`amount`** | Requis pour la plupart des types | `importo`, `value`, `cash`, `cash_amount`, `total`, `totale`, `net_amount`, `gross_amount`, `price` | Impact sur la trésorerie. **Négatif quand l'argent sort, positif quand il entre.** Vide pour TRANSFER et ADJUSTMENT. |
| **`currency`** | Optionnel (EUR par défaut) | `valuta`, `ccy`, `curr`, `currency_code`, `divisa`, `währung` | Code devise ISO 4217 |
| **`asset`** | Requis pour BUY/SELL/DIVIDEND/TRANSFER/ADJUSTMENT | `symbol`, `ticker`, `isin`, `asset_id`, `instrument`, `strumento`, `security`, `titolo`, `name`, `nome` | Ticker, ISIN, ou nom cohérent pour les actifs non cotés |
| **`description`** | Optionnel | `descrizione`, `notes`, `memo`, `note`, `details`, `dettagli`, `comment`, `commento` | Texte libre |

### Valeurs valides pour `type`

`BUY` · `SELL` · `DIVIDEND` · `INTEREST` · `DEPOSIT` · `WITHDRAWAL` · `FEE` · `TAX` · `TRANSFER` · `ADJUSTMENT` · `FX_CONVERSION` · `CASH_TRANSFER`

---

## 🔗 Voir aussi

- **[CSV Générique — Spécification Technique](../../../developer/backend/brim/generic_csv.md)** — Conventions de signe, patterns P2P, gestion des annulations, conseil LLM
- **[Architecture BRIM](../../../developer/backend/brim/architecture.md)** — Fonctionnement de l'assistant d'importation

