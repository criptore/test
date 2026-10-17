# Face Swap GIF

Une app web locale : tu fournis **une photo d'un visage** et **un GIF animé**, et elle met ce visage sur le ou les visages de chaque image du GIF.

## Installation

Il faut Python 3.10 ou plus récent.

```bash
cd faceswap-gif
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Ensuite, ouvre **http://localhost:7860** dans ton navigateur.

Au premier lancement, l'app télécharge environ 1,5 Go de modèles :

- `buffalo_l` (InsightFace) va dans `~/.insightface`.
- Les autres vont dans `faceswap-gif/models/`.

> Carte NVIDIA : remplace `onnxruntime` par `onnxruntime-gpu` pour aller 10 à 30 fois plus vite. L'app utilise CUDA automatiquement si elle le trouve.
> Sans GPU, compte quelques secondes par image du GIF.

## Les modèles utilisés

| Étape | Modèle | Pourquoi |
|---|---|---|
| Détection + repères du visage | InsightFace **SCRFD** (`buffalo_l`) | Le standard, robuste aux angles et aux petits visages |
| Identité du visage source | **ArcFace** w600k_r50 | Le vecteur d'identité qu'attendent les swappers |
| **Face swap (par défaut)** | **HyperSwap 1B 256** (FaceFusion, 2025) | Le plus récent des modèles « one-shot ». Il travaille en 256×256 au lieu de 128×128, donc le visage est plus net. Il prédit aussi son propre masque de visage, ce qui donne des bords plus propres |
| Face swap (alternative) | **inswapper 128** (InsightFace) | La référence historique (Roop, FaceFusion, Deep-Live-Cam). Ressemblance très forte, mais résolution limitée à 128 px |
| Amélioration (optionnelle) | **GFPGAN 1.4** | Rend le visage plus net. Utile surtout avec inswapper ou sur les grands GIF |

« One-shot » veut dire qu'**une seule photo suffit**, sans entraînement. Pour un GIF, c'est le seul type de modèle pratique : DeepFaceLab demande des heures d'entraînement par visage.

## Options

- **Modèle** : HyperSwap (qualité) ou inswapper (plus rapide).
- **Taille max** : les GIF plus grands sont réduits à cette taille. Plus c'est petit, plus c'est rapide.
- **Améliorer le visage (GFPGAN)** et sa **force** : 0,8 par défaut. Baisse-la si le visage paraît trop « lisse ».
- **Remplacer tous les visages** : par défaut, seul le plus grand visage de chaque image est remplacé.

## Conseils pour un bon résultat

- La photo source doit montrer un visage de face, bien éclairé, sans lunettes de soleil, en bonne résolution.
- Les GIF avec des visages assez grands et peu de flou de mouvement donnent les meilleurs résultats.

## Licences et usage responsable

Les modèles InsightFace (`buffalo_l`, `inswapper_128`) sont réservés à un **usage non commercial ou de recherche**. Les modèles hébergés par FaceFusion ont leurs propres conditions.

N'utilise que des visages de personnes qui ont donné leur accord. Ne crée pas de contenu trompeur, diffamatoire ou à caractère sexuel.
