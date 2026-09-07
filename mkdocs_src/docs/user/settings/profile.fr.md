# 👤 Profil

<div class="screenshot-container" style="max-width: 600px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="profile" alt="Profile">
</div>

L'onglet **Profil** gère votre **identité** dans LibreFolio — qui vous êtes et comment vous vous connectez. Les choix d'affichage (langue, devise, thème) se trouvent en revanche dans **[Préférences](preferences.md)** ; les options à l'échelle de l'instance se trouvent dans l'**[onglet Admin](../../admin/settings.md)**.

## 🔒 Verrouillage de l'édition

L'onglet s'ouvre **verrouillé** : les champs sont en lecture seule tant que vous n'avez pas cliqué sur le bouton ✏️ **crayon** dans l'en-tête. Cela évite les modifications accidentelles. Si vous verrouillez à nouveau l'onglet alors que des modifications ne sont pas enregistrées, une boîte de dialogue de confirmation vous demande si vous souhaitez les abandonner.

Lorsque l'onglet est déverrouillé, chaque champ modifié affiche ses propres boutons **enregistrer** / **annuler**, et l'en-tête propose **tout enregistrer** et **tout annuler** pour les actions groupées.

## 🖼️ Avatar

Survolez votre avatar (lorsque l'onglet est déverrouillé) et cliquez sur l'icône 📷 en superposition pour ouvrir le sélecteur d'images : choisissez une image existante dans la [bibliothèque de fichiers](../files/index.md) ou téléversez-en une nouvelle. Les téléversements passent par l'**[outil de recadrage d'image](../misc/image-crop.md)** avec le préréglage *avatar* (recadrage carré, aperçu circulaire).

L'avatar est enregistré immédiatement et est utilisé dans toute l'application, partout où votre identité est affichée — barre latérale, partage de courtier et listes de collaborateurs.

## ✏️ Nom d'utilisateur, e-mail et date de création

- Les champs **Nom d'utilisateur** et **e-mail** peuvent être modifiés (onglet déverrouillé requis). Les modifications s'appliquent immédiatement à vos identifiants de connexion.
- Le champ **Date de création** est en lecture seule et indique votre date d'inscription.

## 🔐 Sécurité

### 🔑 Changer le mot de passe

<div class="screenshot-container" style="max-width: 500px; margin: 1rem auto;">
 <img class="gallery-img" data-category="settings" data-name="password-modal" alt="Change Password">
</div>

Le bouton **Changer le mot de passe** (toujours disponible, aucun déverrouillage nécessaire) ouvre une fenêtre modale demandant :

1. Votre **mot de passe actuel** (pour vérification)
2. Un **nouveau mot de passe** qui respecte toutes les règles : 8 caractères minimum, au moins une lettre majuscule, une lettre minuscule, un chiffre et un caractère spécial — et il doit être différent du mot de passe actuel
3. La **confirmation** du nouveau mot de passe

Après confirmation, votre session reste active — vous n'avez pas besoin de vous reconnecter.

### 🗑️ Supprimer le compte

Le bouton **Supprimer le compte** supprime définitivement votre utilisateur et tout ce qu'il possède. Pour confirmer, vous devez saisir votre **nom d'utilisateur** dans la boîte de dialogue. La suppression est immédiate : vous êtes déconnecté et redirigé vers la page de connexion.

!!! warning "Irréversible"

    La suppression de votre compte est irréversible : vos courtiers, transactions et paramètres sont supprimés avec lui. Si vous êtes le **seul administrateur** de l'instance, la suppression est refusée — promouvez d'abord un autre utilisateur.

---

## 🔗 Liens connexes

- 🎛️ **[Préférences utilisateur](preferences.md)** — Langue, devise de base et thème
- ⚙️ **[Aperçu des paramètres](index.md)** — Résumé des paramètres généraux
- ℹ️ **[À propos](about.md)** — Informations de version, plugins et journal des modifications
- 🛡️ **[Paramètres globaux](../../admin/settings.md)** — Options à l'échelle de l'instance (admin)
