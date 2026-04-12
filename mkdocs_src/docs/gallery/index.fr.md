# 🖼️ Galerie LibreFolio

Bienvenue dans la galerie visuelle de LibreFolio ! Ici, vous pouvez explorer toutes les fonctionnalités de notre plateforme de gestion de portefeuille à travers des captures d'écran.

## 👁️ Choisissez Votre Vue

<div class="gallery-cards">
 <a href="desktop/" class="gallery-card">
 <span class="gallery-icon">🖥️</span>
 <h3>Version Bureau</h3>
 <p>Expérience complète avec toutes les commandes visibles</p>
 </a>
 <a href="mobile/" class="gallery-card">
 <span class="gallery-icon">📱</span>
 <h3>Vue Mobile</h3>
 <p>Design adaptatif optimisé pour les écrans tactiles</p>
 </a>
</div>

## ✨ Fonctionnalités mises en avant

!!! tip "Ce que vous verrez"

    - **Authentification** : Connexion sécurisée avec indicateur de force du mot de passe
    - **Tableau de bord** : Aperçu rapide de votre portefeuille
    - **Courtiers** : Gérez plusieurs comptes de courtage
    - **Fichiers** : Importez et gérez les rapports de courtage avec des vues en grille et en tableau
    - **Paramètres** : Personnalisez votre expérience en 4 langues
    - **Profil** : Gestion de l'avatar et paramètres du compte
    - **Média & Téléversement** : Recadrage/édition d'images, sélecteur d'actifs, renommage de fichiers
    - **Taux de change** : Paires de devises, graphiques, synchronisation, éditeur de données, import CSV
    - **Actifs** : Suivez les actions, ETF, obligations, crypto avec graphiques, signaux, mesures & classification

## 🌍 Support Linguistique

LibreFolio est disponible en :

| Langue | Drapeau | Statut |
|----------|------|------------|
| English | 🇬🇧 | ✅ Terminé |
| Italiano | 🇮🇹 | ✅ Terminé |
| Français | 🇫🇷 | ✅ Terminé |
| Español | 🇪🇸 | ✅ Terminé |

---

<style>

.gallery-cards {
 display: grid;
 grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
 gap: 1.5rem;
 margin: 2rem 0;
}

.gallery-card {
 display: flex;
 flex-direction: column;
 align-items: center;
 padding: 2rem;
 background: var(--md-code-bg-color);
 border-radius: 12px;
 text-decoration: none !important;
 color: inherit !important;
 transition: transform 0.2s, box-shadow 0.2s;
 border: 2px solid transparent;
}

.gallery-card:hover {
 transform: translateY(-4px);
 box-shadow: 0 8px 24px rgba(0,0,0,0.15);
 border-color: var(--md-primary-fg-color);
}

.gallery-icon {
 font-size: 3rem;
 margin-bottom: 1rem;
}

.gallery-card h3 {
 margin: 0.5rem 0;
 color: var(--md-primary-fg-color);
}

.gallery-card p {
 margin: 0;
 text-align: center;
 opacity: 0.8;
}
</style>
