# 🎛️ Préférences utilisateur

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="user-preferences" alt="Préférences utilisateur">
</div>

L'onglet **Préférences** gère **l'apparence et le comportement de l'application pour vous** — les modifications ne s'appliquent qu'à votre compte. Vos informations d'identité (nom d'utilisateur, e-mail, avatar, mot de passe) se trouvent quant à elles dans l'onglet **[Profil](profile.md)**.

| Paramètre | Catégorie | Description |
|---------|----------|-------------|
| **Langue** | 🌍 Affichage | Langue de l'interface — 🇬🇧 English, 🇮🇹 Italiano, 🇫🇷 Français, 🇪🇸 Español. S'applique immédiatement |
| **Devise de base** | 💰 Devise | Devise d'affichage par défaut pour les valeurs du portefeuille |
| **Thème** | 🎨 Apparence | ☀️ Clair / 🌙 Sombre / 🖥️ Auto (suit votre système d'exploitation) |

<style>
/* Keep the first two columns on one line (long setting names would wrap otherwise) */
article table:first-of-type th:nth-child(-n + 2),
article table:first-of-type td:nth-child(-n + 2) {
 white-space: nowrap;
 min-width: 11rem;
}
</style>

Utilisez la **barre latérale des catégories** à gauche pour filtrer les paramètres visibles.

## 💾 Enregistrement, annulation et réinitialisation

Chaque champ gère son propre état :

- Un champ modifié affiche des boutons **enregistrer** et **annuler** ; l'en-tête propose **tout enregistrer** / **tout annuler** pour les actions groupées.
- Les champs dont la valeur diffère de la **valeur par défaut de l'instance** (définie par l'administrateur dans [Paramètres globaux](../../admin/settings.md)) sont mis en évidence comme n'étant pas la valeur par défaut ; le bouton **réinitialiser** rétablit la valeur par défaut de l'instance pour ce champ, et **tout réinitialiser** rétablit tous les champs à la fois.

---

## 🔗 Voir aussi

- 👤 **[Profil](profile.md)** — Nom d'utilisateur, e-mail, avatar, mot de passe, suppression du compte
- ⚙️ **[Aperçu des paramètres](index.md)** — Résumé des paramètres généraux
- ℹ️ **[À propos](about.md)** — Informations de version, plugins et journal des modifications
- 🛡️ **[Paramètres globaux](../../admin/settings.md)** — Options de l'administrateur et planificateur
