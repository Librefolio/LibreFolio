# ❓ Foire Aux Questions (FAQ)

Bienvenue dans la FAQ de LibreFolio. Vous trouverez ici les réponses aux questions les plus courantes.

## 💬 Questions Générales

### 🤔 Qu'est-ce que LibreFolio ?

LibreFolio est un gestionnaire de portefeuille open-source qui vous offre une vue complète et privée de tous vos investissements. De puissants outils d'analyse transforment vos données en informations exploitables — afin que vous puissiez prendre des décisions éclairées en toute confiance et avec un contrôle total.

### 💰 LibreFolio est-il gratuit ?

Oui ! LibreFolio est entièrement gratuit et open-source sous la [licence AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html). Vous pouvez l'installer sur votre propre serveur et tout gérer vous-même sans frais.

!!! info "Bientôt disponible : plateforme hébergée ☁️"

    Nous travaillons sur une plateforme en ligne pour ceux qui n'ont pas le temps, l'intérêt ou les compétences techniques pour l'auto-hébergement. La version hébergée offrira toutes les fonctionnalités sans aucune configuration, avec des mises à jour automatiques et un support dédié — disponible via un abonnement payant.

### 🤖 Des fonctionnalités d'IA sont-elles prévues ?

Oui ! Notre feuille de route inclut des **assistants basés sur l'IA** pour vous aider à analyser votre portefeuille, repérer les tendances et prendre des décisions mieux informées.

- **Auto-hébergé** : vous pouvez connecter vos propres modèles d'IA et tout gérer indépendamment
- **Plateforme hébergée** : les assistants d'IA seront entièrement intégrés — prêts à l'emploi sans configuration requise, accompagnés d'un support premium

### 📊 Quels actifs puis-je suivre ?

LibreFolio prend en charge :

- **Actions & ETF** — Prix récupérés automatiquement via des fournisseurs de données (ex: yfinance)
- **Cryptomonnaies** — Bientôt disponible
- **Obligations** — Saisie manuelle prise en charge
- **Prêts P2P** — Actifs à rendement programmé
- **Espèces & Dépôts** — Suivez votre liquidité

!!! tip "Il manque quelque chose ? 💡"

    S'il y a une classe d'actifs ou une fonctionnalité que vous aimeriez voir et que nous n'avons pas encore envisagée, nous serions ravis d'en entendre parler ! Ouvrez une [demande de fonctionnalité sur GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) et faites-le nous savoir.

## 🚀 Prise en Main

### 📦 Comment installer LibreFolio ?

Consultez notre [Guide d'Installation](../developer/dev-installation.md) pour des instructions détaillées.

### 👤 Comment créer un compte ?

1. Accédez à la page de connexion
2. Cliquez sur "S'inscrire"
3. Remplissez vos informations
4. Votre compte est prêt à l'emploi !

### 🔑 J'ai oublié mon mot de passe, que faire ?

Actuellement, la réinitialisation du mot de passe se fait via CLI. Contactez l'administrateur de votre instance ou exécutez :

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Dépannage

### 📉 Les prix de mes actifs ne se mettent pas à jour

Vérifiez que :

1. La synchronisation automatique est activée dans les paramètres globaux
2. Vos actifs ont des ISIN ou des symboles valides reconnus par le **fournisseur de données** configuré (ex: [yfinance](https://pypi.org/project/yfinance/) pour les actions et ETF)
3. Le service du fournisseur est disponible (vérifiez les journaux du serveur pour détecter d'éventuelles erreurs)

### 💱 Mes taux FX ne se mettent pas à jour

Vérifiez que :

1. La paire de devises possède au moins un [fournisseur de données configuré](../user/fx/detail/provider.md)
2. L'API du fournisseur est accessible (ECB, FED, BOE, SNB)
3. Vous avez exécuté une [synchronisation](../user/fx/sync.md) pour la plage de dates souhaitée
4. Vérifiez la [chaîne d'approvisionnement des fournisseurs](../user/fx/detail/provider.md) pour les options de fallback

### 🔐 Je ne peux pas me connecter

- Vérifiez votre nom d'utilisateur et votre mot de passe
- Vérifiez si votre compte est activé
- Effacez les cookies du navigateur et réessayez

## 🆘 Besoin d'aide supplémentaire ?

- [Documentation Complète](../index.md)
- [Signaler un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [Discussions GitHub](https://github.com/Alfystar/LibreFolio/discussions)
