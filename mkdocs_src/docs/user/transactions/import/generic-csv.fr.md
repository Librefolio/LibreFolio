# 📄 CSV Générique

Le fournisseur **CSV Générique** est un fallback flexible pour les courtiers qui ne sont pas directement pris en charge. Il permet une correspondance manuelle des colonnes afin que vous puissiez importer depuis n'importe quel export basé sur un fichier CSV.

## Quand l'utiliser

- Votre courtier ne figure pas dans la liste des courtiers pris en charge.
- Un courtier pris en charge a modifié son format d'exportation et le plugin n'a pas encore été mis à jour.
- Vous possédez un tableur personnalisé que vous souhaitez importer.

## Comment ça marche

1. Téléversez votre fichier CSV.
2. LibreFolio affiche les colonnes brutes détectées.
3. Associez chaque colonne au champ LibreFolio correspondant (date, type, actif, quantité, prix, montant, devise, frais).
4. Prévisualisez les lignes analysées et confirmez l'importation.

!!! tip "Ajouter un plugin natif"

    Si vous utilisez un courtier fréquemment, envisagez de contribuer en créant un plugin natif. Consultez le [Manuel du Développeur → Guide du Plugin BRIM](../../../developer/backend/brim/generic_csv.md) pour les instructions.

## 🔗 Référence Développeur

→ [Fournisseur CSV Générique — Détails d'implémentation](../../../developer/backend/brim/generic_csv.md)
