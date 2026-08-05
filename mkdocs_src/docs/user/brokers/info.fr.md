# ⚙️ Configuration du courtier et export IA

L'onglet **Info** regroupe la configuration des métadonnées, les contrôles de sécurité, l'outil d'export IA ciblé et le panneau de configuration du partage.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vue des informations et du partage du courtier">
</div>

---

## ⚙️ Métadonnées et paramètres

La colonne de gauche de l'onglet Info affiche les propriétés clés et les règles de validation de ce courtier :

- **Statut du courtier** : Indique si le compte est actuellement `Active`. Les courtiers inactifs sont masqués dans les menus déroulants, mais leurs valeurs historiques sont conservées dans les graphiques.
- **Dates** : Affiche la date d'ouverture du compte et la date de création dans LibreFolio.
- **Devise de base** : La devise de base du compte (toutes les transactions et valorisations sont converties en interne vers cette devise à l'aide des taux de change historiques pour le reporting local).
- **Autoriser le découvert de trésorerie** : Un interrupteur permettant de contourner les erreurs de solde négatif. Lorsqu'il est désactivé, LibreFolio bloque les transactions (comme les achats ou les retraits) qui entraîneraient un solde de trésorerie négatif.
- **Autoriser les positions courtes** : Un interrupteur permettant d'autoriser des quantités d'actifs négatives. Lorsqu'il est désactivé, toute vente au-delà de la taille de votre position ouverte actuelle est bloquée.

---

## 🧠 Export IA ciblé

En haut à droite de la barre d'outils du courtier, **Export IA** (:material-brain:) ouvre trois tâches dédiées au courtier—et non des prompts de portefeuille filtrés :

- **Examen du courtier**
- **Performance du courtier et moteurs du marché**
- **Stratégies de compensation des pertes en capital**

L'instantané côté serveur est limité au courtier sélectionné et peut inclure ses liquidités, ses positions, son activité, ses performances, ses coûts, sa concentration et ses lots FIFO selon la tâche sélectionnée. Des contrôles d'accès côté serveur empêchent d'exporter un courtier auquel l'utilisateur actuel ne peut pas accéder. LibreFolio copie uniquement le résultat dans le presse-papiers ; examinez les données financières sensibles avant de les partager. Voir [Export IA du courtier](../ai-export/broker.md) ou l'[aperçu de l'export IA](../ai-export/index.md).

---

## 🤝 Panneau de partage d'accès

La colonne de droite de l'onglet Info héberge le gestionnaire intégré **Partage du courtier**. Vous pouvez y :

- Inviter d'autres utilisateurs par leur adresse e-mail ou leur nom d'utilisateur.
- Définir leur niveau d'autorisation (Propriétaire, Éditeur, Lecteur).
- Configurer les pourcentages de propriété.

Pour une explication détaillée des règles de partage, des rôles et de la logique des pourcentages, veuillez vous référer à la page dédiée **[Partage du courtier](sharing.md)**.
