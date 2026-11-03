# Apps Fréquence

Chaque app Fréquence en vraie application Android : plein écran, son propre logo, installable à côté des autres.

## Fabriquer les APK

1. Crée un dépôt **privé** sur GitHub (par exemple `frequence-apps`).
2. Envoie-y tout ce dossier, y compris le dossier caché `.github` :
   ```
   git init && git add . && git commit -m "Apps Fréquence"
   git branch -M main
   git remote add origin https://github.com/<toi>/frequence-apps.git
   git push -u origin main
   ```
3. Onglet **Actions** : la compilation démarre toute seule (environ 3 minutes).
4. Une fois finie, l'APK est dans **Releases** → « APK à installer ».

## Installer sur le téléphone

1. Sur le téléphone, ouvre la page **Releases** du dépôt (connecté à GitHub) et télécharge l'APK voulue :
   `Frequence-matin.apk`, `Frequence-job.apk`, `Frequence-revision.apk` ou `Frequence-trail.apk`.
2. Ouvre le fichier. Android demande d'autoriser Chrome à installer des applis : accepte.
3. Ouvre l'app et connecte-toi à claude.ai **avec ton e-mail** et le code reçu.
   Tape le code dans l'app plutôt que de cliquer sur le lien du mail, qui ouvrirait Chrome.

Pour une mise à jour : reviens dans Releases, télécharge la nouvelle APK et installe-la par-dessus (tu restes connecté).

## Ajouter une app

Dans `app/build.gradle.kts`, ajoute un bloc dans `productFlavors` (nom, lien), puis son icône dans
`app/src/<nom>/res/` (même structure que `app/src/matin/res/`).

La clé `app/frequence.keystore` signe les APK. Garde le dépôt privé.
