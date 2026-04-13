# Guide de Dépannage OCR

## Problème courant : L'OCR retourne des résultats vides ou des notes de 0

### Causes possibles

1. **Mauvaise qualité d'image**
   - Les photos de documents avec un téléphone sont souvent de mauvaise qualité
   - Éclairage insuffisant, ombres, flou
   - Image de travers ou déformée

2. **Format de document incorrect**
   - L'OCR est optimisé pour des copies d'examen avec le format :
     ```
     ID: 123456
     Nom: Étudiant
     1 A
     2 B
     3 C
     4 D
     ```
   - Si le document utilise un autre format, les réponses ne seront pas détectées

3. **Images sans texte**
   - Si vous essayez de traiter des photos ou des images qui ne contiennent pas de texte

### Solutions

#### 1. Utiliser des scans de qualité
```
✓ Bon format :
- Scans au format PDF ou JPEG haute résolution
- Document plat, bien aligné
- Texte clair et lisible
- Format standardisé avec numérotation claire

✗ Mauvais format :
- Photos prises avec un téléphone
- Documents pliés ou de travers
- Écriture manuscrite difficile à lire
- Images sombres ou floues
```

#### 2. Vérifier le format des réponses
L'OCR reconnaît ces formats de réponses :
- `1 A` ou `1. A` ou `1: A`
- `1A` (sans espace)
- `Q1: A`

#### 3. Tester avec une image de référence
Utilisez cette image de test pour vérifier que l'OCR fonctionne :
```
[ID: 123456]
[NOM: Test Étudiant]
[1 A]
[2 B]
[3 C]
[4 D]
```

### Messages d'erreur fréquents

#### "L'OCR a échoué : aucun texte extrait de l'image"
- L'image ne contient pas de texte lisible
- Essayez avec un scan de meilleure qualité

#### "Aucune réponse QCM trouvée"
- Le document ne contient pas de réponses au format A/B/C/D
- Vérifiez que c'est bien une copie d'examen QCM

### Améliorations apportées

Le code a été amélioré pour :
1. Essayer plusieurs configurations de Tesseract si la première échoue
2. Donner des messages d'erreur plus détaillés
3. Ajouter des avertissements quand aucune réponse n'est trouvée
4. Mieux gérer les erreurs de format d'image

### Étapes de dépannage

1. Vérifiez que vous utilisez bien un **scan** et non une photo
2. Assurez-vous que le texte est **lisible** à l'œil nu
3. Vérifiez le **format** des réponses (numéro + lettre A/B/C/D)
4. Testez avec l'application en mode débogage pour voir les logs détaillés