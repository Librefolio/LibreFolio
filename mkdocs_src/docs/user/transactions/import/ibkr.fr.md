# 🏦 Interactive Brokers (IBKR)

!!! info "Bêta"

    Ce plugin est en version **Bêta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## Comment exporter

1. Connectez-vous au [Portail Client Interactive Brokers](https://www.interactivebrokers.com) ou à Trader Workstation (TWS).
2. Allez dans **Reports → Activity → Flex Queries** ou **Statements → Activity Statement**.
3. Sélectionnez la plage de dates et exportez au format **CSV**.

## Notes

- Prise en charge des rapports d'activité standard d'IBKR (transactions, dividendes, frais, dépôts, retraits).
- Les comptes multi-devises sont pris en charge.
- Les opérations sur titres (divisions, fusions) peuvent nécessiter un ajustement manuel.

## 🔗 Référence Développeur

→ [Fournisseur IBKR — Détails d'implémentation](../../../developer/backend/brim/providers_list.md)
