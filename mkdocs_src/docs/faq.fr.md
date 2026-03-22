# ❓ Foire aux questions (FAQ)

Bienvenue dans la FAQ de LibreFolio. Vous y trouverez des réponses aux questions courantes.

## 💬 Questions générales

### 🤔 Qu'est-ce que LibreFolio ?

LibreFolio est un tracker de portefeuille auto-hébergé et open source, conçu pour les investisseurs soucieux de leur vie privée. Il vous permet de suivre vos investissements, d'analyser leurs performances et de conserver le contrôle total de vos données financières.

### 💰 LibreFolio est-il gratuit ?

Oui ! LibreFolio est entièrement gratuit et open source sous licence MIT.

### 📊 Quels actifs puis-je suivre ?

LibreFolio prend en charge :

- **Actions et ETF** - Prix automatiquement récupérés via yfinance
- **Cryptomonnaies** - Bientôt disponibles
- **Obligations** - Saisie manuelle prise en charge
- **Prêts P2P** - Actifs à rendement périodique
- **Espèces et Dépôts** - Suivi des liquidités

## 🚀 Démarrer

### 📦 Comment installer LibreFolio ?

Consultez notre [Guide d'installation](developer/dev-installation.md) pour des instructions détaillées.

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

### 📉 Mes prix ne se mettent pas à jour

Vérifiez que :

1. La synchronisation automatique est activée dans les Paramètres globaux
2. Vos actifs possèdent des ISIN ou symboles valides
3. Le fournisseur yfinance fonctionne (consultez les journaux)

### 🔐 Je ne peux pas me connecter

- Vérifiez votre nom d'utilisateur et mot de passe
- Vérifiez si votre compte est activé
- Effacez les cookies du navigateur et réessayez

## 🆘 Besoin de plus d'aide ?

- [Documentation complète](index.md)
- [Signaler un bug](https://github.com/Alfystar/LibreFolio/issues)
- [Discussions GitHub](https://github.com/Alfystar/LibreFolio/discussions)
