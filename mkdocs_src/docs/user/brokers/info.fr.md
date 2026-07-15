# ⚙️ Configuration du courtier & Export IA

L'onglet **Informations** héberge la configuration des métadonnées, les contrôles de sécurité, l'outil d'export IA ciblé, et le panneau de configuration du partage.

<div class="screenshot-container" style="max-width: 700px; margin: 1.5rem auto 2rem auto;">
 <img class="gallery-img" data-category="brokers" data-name="info-tab" alt="Vue des informations et du partage du courtier">
</div>

---

## ⚙️ Métadonnées & Paramètres

La colonne de gauche de l'onglet Informations affiche les propriétés clés et les règles de validation pour ce courtier :

- **Statut du courtier** : Indique si le compte est actuellement `Actif`. Les courtiers inactifs sont masqués des menus déroulants mais leurs valeurs historiques sont conservées dans les graphiques.
- **Dates** : Affiche la date d'ouverture du compte et sa date de création dans LibreFolio.
- **Devise de base** : La devise de base du compte (toutes les transactions et évaluations sont converties en interne en utilisant les taux de change historiques vers cette devise pour les rapports locaux).
- **Autoriser le découvert** : Un interrupteur pour contourner les erreurs de solde négatif. Lorsqu'il est désactivé, LibreFolio bloque les transactions (comme les achats ou les retraits) qui entraîneraient un solde de trésorerie négatif.
- **Autoriser les positions short** : Un interrupteur pour autoriser les quantités d'actifs négatives. Lorsqu'il est désactivé, la vente d'une quantité supérieure à votre position ouverte actuelle est bloquée.

---

## 🧠 Export IA ciblé

En haut à droite de la barre d'outils du courtier, le bouton **Export IA** (:material-brain:) copie dans votre presse-papiers une représentation textuelle structurée de l'état actuel du courtier.

Cet export est **spécifiquement ciblé sur ce courtier** (contrairement au bouton du tableau de bord principal qui copie les données pour l'ensemble du portefeuille). Il agrège :

- Les soldes de trésorerie locaux.
- Les avoirs et quantités d'actifs locaux.
- Les pondérations d'allocation actives.

Vous pouvez coller cette invite structurée directement dans votre LLM préféré (comme Gemini ou ChatGPT) pour une analyse ciblée et personnalisée de ce compte spécifique.

---

## 🤝 Panneau de partage d'accès

La colonne de droite de l'onglet Informations héberge le gestionnaire de **partage de courtier** intégré. Vous pouvez ici :

- Inviter d'autres utilisateurs par leur email ou nom d'utilisateur.
- Définir leur autorisation de rôle (Propriétaire, Éditeur, Lecteur).
- Configurer les pourcentages de propriété.

Pour une explication détaillée des règles de partage, des rôles et de la logique des pourcentages, veuillez vous référer à la page **[Partage de courtier](sharing.md)** dédiée.
