# S&P500 Analysis Web App

Een complete webapp voor S&P500-analyse op basis van CSV-uploads uit TradingView. De applicatie verwerkt historische OHLCV-data en berekent technische indicatoren zoals RSI en MACD.

## Features

- **CSV Upload**: Upload TradingView CSV-bestanden met S&P500 data
- **Data Processing**: Automatische data cleaning en validatie
- **Technical Indicators**:
  - RSI (14-day Relative Strength Index met Wilder's smoothing)
  - MACD (12-26-9)
  - High - Previous Close verschil
- **Dashboard**: Interactieve tabel met de laatste 60 dagen
- **Sorteerbare kolommen**: Klik op kolomhoofden om te sorteren
- **RSI Highlighting**: Visuele indicatie voor overbought (>70) en oversold (<30) condities

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **Pandas**: Data verwerking en analyse
- **NumPy**: Numerieke berekeningen
- **SQLite**: Lightweight database voor data opslag

### Frontend
- **Vanilla JavaScript**: Geen dependencies
- **HTML5/CSS3**: Modern responsive design
- **Fetch API**: Asynchrone API communicatie

## Project Structuur

```
tradingview-predictions/
├── backend/
│   └── main.py              # FastAPI applicatie
├── frontend/
│   ├── index.html           # Dashboard pagina
│   ├── upload.html          # Upload pagina
│   ├── dashboard.js         # Dashboard logica
│   ├── upload.js            # Upload logica
│   └── styles.css           # Styling
├── data/                    # CSV bestanden (git ignored behalve samples)
├── requirements.txt         # Python dependencies
└── README.md
```

## Installatie

### 1. Clone de repository

```bash
cd tradingview-predictions
```

### 2. Installeer Python dependencies

```bash
pip install -r requirements.txt
```

Of gebruik een virtual environment (aanbevolen):

```bash
python -m venv venv
source venv/bin/activate  # Op Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Gebruik

### Optie A: Quick Start (Aanbevolen)

Gebruik het meegeleverde start script dat automatisch backend en frontend start:

```bash
./run.sh
```

Dit script start:
- Backend op `http://localhost:8000`
- Frontend op `http://localhost:3000`

Druk op `Ctrl+C` om beide servers te stoppen.

### Optie B: Handmatig Starten

#### 1. Start de Backend

```bash
cd backend
python main.py
```

De API draait nu op `http://localhost:8000`

Je kunt de API documentatie bekijken op:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### 2. Start de Frontend

Open de frontend in een lokale webserver. Je kunt bijvoorbeeld Python's built-in HTTP server gebruiken:

```bash
cd frontend
python -m http.server 3000
```

Of gebruik een andere webserver naar keuze (Live Server in VS Code, etc.)

Open je browser op `http://localhost:3000`

### 3. Upload CSV Data

1. Ga naar de "Data Upload" pagina
2. Sleep een CSV-bestand in het upload gebied of klik "Selecteer Bestand"
3. Klik "Upload en Verwerk"
4. Wacht tot de verwerking klaar is
5. Ga naar het Dashboard om de data te bekijken

**Voorbeeldbestanden**: In de `data/` folder staan twee voorbeeldbestanden die je kunt gebruiken om de app te testen:
- `OANDA_SPX500USD, 1D_53cca.csv` - Dagelijkse data
- `SP_SPX, 1M_db940.csv` - Maandelijkse data (van 2000-2024)

Beide bestanden bevatten S&P500 data in het juiste TradingView formaat.

### 4. Test de Backend (Optioneel)

Je kunt de backend testen met het meegeleverde test script:

```bash
python test_backend.py
```

Dit script test automatisch:
- ✅ API health check
- ✅ CSV upload met voorbeelddata
- ✅ Data statistics endpoint
- ✅ Daily data endpoint met indicator berekeningen

## CSV Formaat

Het CSV-bestand moet de volgende kolommen bevatten:

| Kolom | Voorbeeld | Beschrijving |
|-------|-----------|--------------|
| `time` | 2024-11-21 | Datum (YYYY-MM-DD) of datetime |
| `open` | 4540.25 | Opening prijs |
| `high` | 4575.12 | Hoogste prijs van de dag |
| `low` | 4525.90 | Laagste prijs van de dag |
| `close` | 4568.70 | Sluitingsprijs |
| `volume` | 1.2345e7 | Handelsvolume |

**Opmerking**: Het CSV-bestand mag extra kolommen bevatten (zoals bestaande RSI/MACD berekeningen uit TradingView). Deze worden genegeerd en alle indicatoren worden opnieuw berekend.

## API Endpoints

### POST `/api/upload`
Upload en verwerk een CSV-bestand

**Request**: `multipart/form-data` met CSV file

**Response**:
```json
{
  "status": "success",
  "message": "CSV uploaded and processed successfully",
  "records_processed": 5000,
  "date_range": {
    "start": "2000-12-01",
    "end": "2024-11-21"
  }
}
```

### GET `/api/daily-data?limit=60`
Haal de laatste N dagen op

**Query Parameters**:
- `limit` (optional): Aantal dagen (default: 60)

**Response**:
```json
[
  {
    "date": "2024-11-21",
    "open": 4540.25,
    "high": 4575.12,
    "low": 4525.90,
    "close": 4568.70,
    "volume": 12345000,
    "high_prev_close_diff": 6.42,
    "rsi": 58.3,
    "macd": {
      "line": 12.84,
      "signal": 10.12,
      "hist": 2.72
    }
  }
]
```

### GET `/api/stats`
Krijg statistieken over de opgeslagen data

**Response**:
```json
{
  "total_records": 5000,
  "date_range": {
    "start": "2000-12-01",
    "end": "2024-11-21"
  }
}
```

## Technische Indicatoren

### RSI (Relative Strength Index)
- **Periode**: 14 dagen
- **Methode**: Wilder's smoothing (klassieke RSI)
- **Interpretatie**:
  - RSI > 70: Overbought (rood gemarkeerd)
  - RSI < 30: Oversold (groen gemarkeerd)

### MACD (Moving Average Convergence Divergence)
- **MACD Line**: EMA(12) - EMA(26)
- **Signal Line**: EMA(9) van MACD
- **Histogram**: MACD - Signal

### High - Previous Close
Het verschil tussen de high van vandaag en de close van gisteren. Nuttig voor gap-analyse.

## Development

### Backend wijzigen

De backend code staat in [backend/main.py](backend/main.py). Na wijzigingen:

```bash
# Stop de server (Ctrl+C)
# Start opnieuw
python backend/main.py
```

### Frontend wijzigen

HTML, CSS en JavaScript bestanden worden automatisch herladen als je een webserver met hot-reload gebruikt (zoals Live Server in VS Code).

## Database

De app gebruikt SQLite voor data opslag. De database file (`sp500_data.db`) wordt automatisch aangemaakt in de `backend/` directory.

**Opmerking**: Bij elke nieuwe CSV upload wordt de database overschreven met de nieuwe data.

## Troubleshooting

### Backend start niet
- Check of Python 3.8+ geïnstalleerd is
- Controleer of alle dependencies geïnstalleerd zijn: `pip install -r requirements.txt`
- Kijk naar error messages in de terminal

### Frontend kan geen verbinding maken met API
- Zorg dat de backend draait op `http://localhost:8000`
- Check CORS instellingen als je een andere port gebruikt
- Open de browser console (F12) voor error messages

### CSV upload mislukt
- Controleer of het CSV-bestand alle vereiste kolommen heeft
- Check of de data het juiste formaat heeft
- Bekijk de error message voor specifieke details

### Geen data in Dashboard
- Upload eerst een CSV-bestand op de Data Upload pagina
- Check of de upload succesvol was
- Vernieuw de pagina met de "Vernieuw Data" knop

## License

Dit project is gemaakt voor persoonlijk gebruik.
