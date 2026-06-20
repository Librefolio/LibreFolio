# <img src="https://www.directa.it/favicon.ico" alt=""> Directa SIM

!!! info "Bêta"

    Ce plugin est en version **Bêta** — testé avec des fichiers d'exemple, mais des cas particuliers peuvent exister.

## 📥 Comment exporter

Pour exporter vos transactions depuis Directa SIM :

1. Connectez-vous à votre [Portail Directa](https://www.directatrading.com) (en utilisant l'interface dLite ou Classic).
2. Allez dans **INFO** ou **Operazioni** dans le menu principal, puis sélectionnez **Movimenti** (Mouvements de trésorerie) ou **Tabella Ordini** (Historique des ordres).
3. Sélectionnez la plage de dates que vous souhaitez exporter.
4. Cliquez sur l'icône de téléchargement **CSV** ou sur le bouton d'exportation en haut à droite du tableau.
5. Enregistrez le fichier directement sans l'ouvrir ni le modifier dans Excel.

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <!-- [Screenshot Placeholder: Directa SIM Portal - Movimenti Cash / Transazioni CSV export page] -->
</div>

## ⚠️ Pièges courants

!!! warning "Lignes d'en-tête"

    Les fichiers Directa SIM contiennent un bloc d'en-tête de métadonnées (généralement 9 lignes) avant le tableau de données réel. Le parseur est conçu pour ignorer ce bloc automatiquement. **Ne supprimez pas ces lignes d'en-tête manuellement**, sinon le parseur ne pourra pas trouver les colonnes de données correctes.

!!! warning "Délimiteurs"

    Les exports Directa utilisent le point-virgule `;` comme délimiteur et le formatage numérique italien standard (virgule `,` pour les décimales). Le parseur analyse ces paramètres automatiquement. Évitez d'enregistrer le CSV via un logiciel qui convertit ces délimiteurs (comme l'ouverture et l'enregistrement dans Microsoft Excel sans paramètres de texte brut).

## 📝 Notes

- Prise en charge des transactions d'actions, d'obligations et d'ETF, des dividendes, des taxes (ritenute fiscali) et des frais de transaction.
- Les opérations de compte sont libellées en EUR.

## 🔗 Référence développeur

→ [Fournisseur Directa SIM — Détails d'implémentation](../../../developer/backend/brim/providers_list.md)
