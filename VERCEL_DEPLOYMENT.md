# S&P500 Analysis - Vercel Deployment Guide

Deze guide legt uit hoe je de S&P500 Analysis app deployt op Vercel.

## ⚠️ Belangrijke Opmerking over Data Persistentie

**LET OP:** De huidige Vercel configuratie gebruikt `/tmp` storage, wat betekent dat **geüploade data verloren gaat** bij elke nieuwe deployment of wanneer de serverless function opnieuw opstart.

### Oplossingen voor Permanente Data Opslag:

#### Optie 1: Vercel Postgres (Aanbevolen)
- Permanente database opslag
- Gratis tier beschikbaar (60 uur compute time per maand)
- Beste prestaties

#### Optie 2: Externe Database (Supabase, PlanetScale, Neon)
- Gratis tiers beschikbaar
- Onafhankelijk van Vercel
- Eenvoudig te migreren

#### Optie 3: Vercel KV (Redis)
- Eenvoudige key-value store
- Gratis tier beschikbaar
- Snel maar minder flexibel

**Voor deze deployment gebruiken we de /tmp oplossing (data is tijdelijk).** Zie onderaan voor instructies om Vercel Postgres toe te voegen.

---

## Stap 1: Vercel Account Aanmaken

1. Ga naar [vercel.com](https://vercel.com)
2. Klik op "Sign Up"
3. Maak een account aan met GitHub, GitLab, of Bitbucket (GitHub wordt aanbevolen)

## Stap 2: Project Voorbereiden met Git

### A. GitHub Repository Aanmaken

1. Ga naar [github.com](https://github.com)
2. Klik op "New repository"
3. Naam: `sp500-analysis` (of een andere naam)
4. Kies "Public" of "Private"
5. **NIET** "Initialize with README" aanvinken
6. Klik "Create repository"

### B. Lokaal Project naar GitHub Pushen

Open een terminal in je project folder en voer uit:

```bash
# Ga naar je project folder
cd /Users/alex/Documents/personal/Trading_view_predictions/tradingview-predictions

# Initialiseer git (als nog niet gedaan)
git init

# Voeg een .gitignore toe
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/

# Database
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Vercel
.vercel

# Logs
*.log

# Temporary files
/tmp/
EOF

# Voeg alle bestanden toe
git add .

# Maak eerste commit
git commit -m "Initial commit: S&P500 Analysis App"

# Voeg remote toe (vervang USERNAME met je GitHub username)
git remote add origin https://github.com/USERNAME/sp500-analysis.git

# Push naar GitHub
git branch -M main
git push -u origin main
```

## Stap 3: Project Deployen op Vercel

### Via Vercel Dashboard:

1. Log in op [vercel.com/dashboard](https://vercel.com/dashboard)
2. Klik op "Add New..." → "Project"
3. Importeer je GitHub repository:
   - Klik "Import" naast je `sp500-analysis` repository
   - Als je het niet ziet, klik "Adjust GitHub App Permissions"
4. Configure Project:
   - **Framework Preset:** Selecteer "Other"
   - **Root Directory:** Laat leeg (gebruik `./`)
   - **Build Settings:** Laat standaard
5. Klik "Deploy"

Vercel zal nu je applicatie bouwen en deployen. Dit duurt ongeveer 1-2 minuten.

## Stap 4: Test de Deployment

Als de deployment klaar is:

1. Klik op de gegenereerde URL (bijv. `https://sp500-analysis.vercel.app`)
2. Je zou je applicatie moeten zien
3. Test de upload functionaliteit:
   - Ga naar "Data Upload (1D)"
   - Upload een CSV bestand
   - Controleer het Dashboard

## Stap 5: Custom Domain (Optioneel)

1. Ga naar je project in Vercel Dashboard
2. Klik op "Settings" → "Domains"
3. Voeg je custom domain toe (bijv. `sp500.jouwdomein.nl`)
4. Volg de instructies om DNS in te stellen

---

## Updates Deployen

Elke keer dat je code wijzigingen pusht naar GitHub, zal Vercel automatisch deployen:

```bash
# Maak wijzigingen in je code
git add .
git commit -m "Beschrijving van wijzigingen"
git push
```

Vercel zal binnen enkele seconden beginnen met deployen.

---

## Vercel Postgres Toevoegen (Voor Permanente Data Opslag)

### Stap 1: Vercel Postgres Aanmaken

1. Ga naar je project in Vercel Dashboard
2. Klik op "Storage" tab
3. Klik "Create Database"
4. Selecteer "Postgres"
5. Geef een naam (bijv. `sp500-db`)
6. Selecteer een regio (kies dichtbij je gebruikers)
7. Klik "Create"

### Stap 2: Database Connectie Configureren

Vercel zal automatisch environment variables toevoegen:
- `POSTGRES_URL`
- `POSTGRES_PRISMA_URL`
- `POSTGRES_URL_NON_POOLING`

### Stap 3: Update API Code

Update `api/index.py` om Postgres te gebruiken in plaats van /tmp storage:

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Database connection
DATABASE_URL = os.getenv('POSTGRES_URL')

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# Initialiseer database tables
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Maak daily_data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_data (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            high_prev_close_diff REAL,
            rsi REAL,
            macd_line REAL,
            macd_signal REAL,
            macd_hist REAL
        )
    """)

    # Maak monthly_data table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_data (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL
        )
    """)

    conn.commit()
    conn.close()

# Roep init_db() aan bij startup
init_db()
```

### Stap 4: Update requirements.txt

Voeg toe aan `api/requirements.txt`:
```
psycopg2-binary==2.9.9
```

### Stap 5: Redeploy

```bash
git add .
git commit -m "Add Postgres support"
git push
```

---

## Environment Variables

Als je custom environment variables nodig hebt:

1. Ga naar je project in Vercel Dashboard
2. Klik "Settings" → "Environment Variables"
3. Voeg variabelen toe
4. Redeploy het project

---

## Troubleshooting

### Deployment Fails

1. Check de build logs in Vercel Dashboard
2. Veelvoorkomende problemen:
   - Python versie mismatch
   - Missing dependencies in requirements.txt
   - Syntax errors in code

### API Errors

1. Check de Function Logs:
   - Vercel Dashboard → Your Project → Functions tab
   - Klik op een function om logs te zien
2. Test de API endpoints:
   - `https://jouw-url.vercel.app/api/health`
   - Zou `{"status": "healthy"}` moeten retourneren

### Data Verdwijnt

- Dit is normaal met /tmp storage
- Upgrade naar Vercel Postgres (zie hierboven)
- Of gebruik een externe database

---

## Kosten

### Gratis Tier:
- 100GB bandwidth per maand
- 100 uur serverless function execution time
- Onbeperkte deployments
- 1 Vercel Postgres database (60 uur compute time)

Dit is **meer dan voldoende** voor persoonlijk gebruik en kleine projecten.

### Pro Tier ($20/maand):
- Meer bandwidth en execution time
- Custom domains zonder Vercel branding
- Password protection
- Analytics

Voor deze app is de **gratis tier voldoende**.

---

## Handige Vercel CLI Commands

Installeer Vercel CLI (optioneel):

```bash
npm install -g vercel
```

Gebruik:

```bash
# Deploy vanuit command line
vercel

# Deploy naar productie
vercel --prod

# Check deployment status
vercel ls

# Bekijk logs
vercel logs
```

---

## Support

Voor problemen of vragen:
- Vercel Docs: [vercel.com/docs](https://vercel.com/docs)
- Vercel Discord: [vercel.com/discord](https://vercel.com/discord)
- Deze app's GitHub Issues

---

## Samenvatting Deployment Flow

1. ✅ Vercel account aanmaken
2. ✅ GitHub repository aanmaken en code pushen
3. ✅ Project importeren in Vercel
4. ✅ Automatische deployment
5. 🎉 App is live!

Optioneel:
- Vercel Postgres toevoegen voor permanente data
- Custom domain configureren
- Environment variables instellen

**Je app is nu live op: `https://jouw-project.vercel.app`**
