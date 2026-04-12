# ❓ Foire Aux Questions (FAQ)

Bienvenue dans la FAQ de LibreFolio. Vous trouverez ici les réponses aux questions les plus courantes.

## 💬 Questions Générales

### 🤔 Qu'est-ce que LibreFolio ?

LibreFolio est un outil de suivi de portefeuille open-source et auto-hébergé, conçu pour les investisseurs soucieux de leur confidentialité. Il vous permet de suivre vos investissements, d'analyser vos performances et de garder le contrôle total de vos données financières.

### 💰 LibreFolio est-il gratuit ?

Oui ! LibreFolio est entièrement gratuit et open-source sous la [licence AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html).

### 📊 Quels actifs puis-je suivre ?

LibreFolio prend en charge :

- **Actions & ETF** — Prix récupérés automatiquement via des fournisseurs de données (ex: yfinance)
- **Cryptomonnaies** — Bientôt disponible
- **Obligations** — Saisie manuelle prise en charge
- **Prêts P2P** — Actifs à rendement programmé
- **Espèces & Dépôts** — Suivez votre liquidité

!!! tip "Il manque quelque chose ? 💡"

    Si vous souhaitez voir une classe d'actifs ou une fonctionnalité à laquelle nous n'avons pas encore pensé, nous serions ravis de recevoir vos suggestions ! Ouvrez une [demande de fonctionnalité sur GitHub](https://github.com/Alfystar/LibreFolio/issues/new?labels=enhancement) et faites-le nous savoir.

## 🚀 Prise en main

### 📦 Comment installer LibreFolio ?

Consultez notre [Guide d'Installation](developer/dev-installation.md) pour des instructions détaillées.

### 👤 Comment créer un compte ?

1. Accédez à la page de connexion
2. Cliquez sur "S'inscrire"
3. Remplissez vos informations
4. Votre compte est prêt à l'emploi !

### 🔑 J'ai oublié mon mot de passe, que faire ?

Actuellement, la réinitialisation du mot de passe s'effectue via CLI. Contactez l'administrateur de votre instance ou exécutez :

```bash
./dev.py user reset <username> <new_password>
```

## 🔧 Dépannage

### 📉 Les prix de mes actifs ne se mettent pas à jour

Vérifiez que :

1. La synchronisation automatique est activée dans les Paramètres globaux
2. Vos actifs possèdent des ISIN ou des symboles valides reconnus par le **fournisseur de données** configuré (ex: [yfinance](https://pypi.org/project/yfinance/) pour les actions et ETF)
3. Le service du fournisseur est disponible (vérifiez les journaux du serveur pour détecter d'éventuelles erreurs)

### 💱 Mes taux de change ne se mettent pas à jour

Vérifiez que :

1. La paire de devises possède au moins un [fournisseur de données configuré](user/fx/detail/provider.md)
2. L'API du fournisseur est joignable (ECB, FED, BOE, SNB)
3. Vous avez lancé une [synchronisation](user/fx/sync.md) pour la plage de dates souhaitée
4. Vérifiez la [chaîne d'approvisionnement du fournisseur](user/fx/detail/provider.md) pour les options de fallback

### 🔐 Je ne peux pas me connecter

- Vérifiez votre nom d'utilisateur et votre mot de passe
- Vérifiez si votre compte est activé
- Effacez les cookies du navigateur et réessayez

## 🆘 Besoin de plus d'aide ?

- [Documentation Complète](index.md)
- [Signaler un Bug](https://github.com/Alfystar/LibreFolio/issues)
- [Discussions GitHub](https://github.com/Alfystar/LibreFolio/discussions)
