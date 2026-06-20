# 🛡️ Paramètres Globaux

<div class="screenshot-container" style="max-width: 700px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="global-settings" alt="Paramètres Globaux (Admin)">
</div>

!!! warning "Admin access required"

    L'onglet **Paramètres Globaux** n'est visible que pour les utilisateurs possédant le rôle **ADMIN**.

Les paramètres globaux affectent tous les utilisateurs de l'instance :

| Paramètre | Description |
|-----------|-------------|
| **Inscription** | Activer ou désactiver l'auto-inscription des nouveaux utilisateurs |
| **Langue par défaut** | Langue fallback pour les nouveaux utilisateurs |
| **Devise par défaut** | Devise de base par défaut pour les nouveaux comptes |
| **Délai de session** | Délai d'expiration pour inactivité en minutes |
| **Planificateur** | Activer ou désactiver le démon de synchronisation automatique des données de marché en arrière-plan |

---

## 🕐 Planificateur de Données de Marché

Lorsque le planificateur d'arrière-plan est activé, les administrateurs peuvent configurer les paramètres de synchronisation et inspecter les journaux d'exécution directement depuis l'interface utilisateur.

### ⚙️ Configurer le Planificateur

Cliquez sur le bouton **Configurer** de la ligne Planificateur pour personnaliser les fréquences d'exécution et les paramètres :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-config" alt="Modale de Configuration du Planificateur">
</div>

* **Fréquence des prix actuels** : La fréquence (en minutes) à laquelle le démon récupère les cours en direct pour maintenir le cache du tableau de bord actif (par défaut : 10m).
* **Heures de synchronisation historique** : Heures spécifiques de la journée (séparées par des virgules, ex: `06:00,23:00`) pour exécuter les mises à jour historiques des clôtures quotidiennes.
* **Jours de synchronisation historique** : Jours spécifiques de la semaine où la synchronisation historique est exécutée (généralement du lundi au samedi).
* **Horizon historique** : La fenêtre de rétrospective (en jours) pour vérifier les points de prix historiques manquants (par défaut : 14 jours).

### 📜 Journaux du Planificateur

Cliquez sur **Voir les journaux** pour ouvrir l'inspecteur de journaux. Cette modale affiche une liste des exécutions récentes du planificateur :

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="scheduler-log" alt="Modale des Journaux du Planificateur">
</div>

Elle indique l'horodatage de l'exécution, le nom de la tâche, le statut (Success/Error), la durée d'exécution, ainsi que les détails structurés des actifs traités, des flux de prix et d'éventuelles traces d'erreurs.

---

## 🔗 Liens connexes

- ⚙️ **[Aperçu des Paramètres](index.md)** — Résumé des paramètres généraux
- 👤 **[Préférences Utilisateur](preferences.md)** — Préférences de profil et d'affichage
- ℹ️ **[À propos](about.md)** — Informations de version et licence
