from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime
import io
import sys
import traceback

pandas_import_error = None
numpy_import_error = None
try:
    import pandas as pd
except Exception as exc:  # pragma: no cover - defensive for runtime env issues
    pandas_import_error = exc
    pd = None
    traceback.print_exc(file=sys.stderr)
try:
    import numpy as np
except Exception as exc:  # pragma: no cover
    numpy_import_error = exc
    np = None
    traceback.print_exc(file=sys.stderr)
app = FastAPI(title="S&P500 Analysis API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DAILY_DATA_PATH = "/tmp/daily_data.json"
MONTHLY_DATA_PATH = "/tmp/monthly_data.json"


def ensure_dependencies():
    """
    Vercel/Lambda kan falen als binary wheels niet goed laden.
    Geef een duidelijk foutbericht terug in plaats van een generieke 500.
    """
    if pandas_import_error:
        # Log extra context zodat het in Vercel logs zichtbaar is
        print("Pandas import error:", pandas_import_error, file=sys.stderr)
        traceback.print_exception(pandas_import_error, file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"Pandas kon niet geladen worden: {pandas_import_error}"
        )
    if numpy_import_error:
        print("Numpy import error:", numpy_import_error, file=sys.stderr)
        traceback.print_exception(numpy_import_error, file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"Numpy kon niet geladen worden: {numpy_import_error}"
        )
def load_data(path: str) -> List[Dict]:
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []
def save_data(path: str, data: List[Dict]):
    with open(path, 'w') as f:
        json.dump(data, f)
def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    for i in range(period, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * (period - 1) + loss.iloc[i]) / period
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    return data.ewm(span=period, adjust=False).mean()
def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return {
        'line': macd_line,
        'signal': signal_line,
        'hist': histogram
    }
def process_daily_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values('time')
    df['time'] = pd.to_datetime(df['time'], unit='s', errors='ignore')
    if df['time'].dtype == 'object':
        df['time'] = pd.to_datetime(df['time'])
    df['date'] = df['time'].dt.strftime('%Y-%m-%d')
    df['prev_close'] = df['close'].shift(1)
    df['high_prev_close_diff'] = df['high'] - df['prev_close']
    df['rsi'] = calculate_rsi(df['close'])
    macd = calculate_macd(df['close'])
    df['macd_line'] = macd['line']
    df['macd_signal'] = macd['signal']
    df['macd_hist'] = macd['hist']
    df = df.drop(columns=['time', 'prev_close'])
    return df
def process_monthly_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values('time')
    df['time'] = pd.to_datetime(df['time'], unit='s', errors='ignore')
    if df['time'].dtype == 'object':
        df['time'] = pd.to_datetime(df['time'])
    df['date'] = df['time'].dt.strftime('%Y-%m-%d')
    df = df.drop(columns=['time'])
    return df
@app.get("/")
async def root():
    return {"message": "S&P500 Analysis API", "status": "running"}
@app.get("/api/health")
async def health_check():
    ensure_dependencies()
    return {"status": "healthy"}
@app.post("/api/upload")
async def upload_daily_data(file: UploadFile = File(...)):
    ensure_dependencies()
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        processed_df = process_daily_data(df)
        data = processed_df.to_dict('records')
        save_data(DAILY_DATA_PATH, data)
        return {
            "message": "Daily data uploaded and processed successfully",
            "records_processed": len(data),
            "date_range": {
                "start": data[0]['date'] if data else None,
                "end": data[-1]['date'] if data else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
@app.post("/api/upload-monthly")
async def upload_monthly_data(file: UploadFile = File(...)):
    ensure_dependencies()
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        processed_df = process_monthly_data(df)
        data = processed_df.to_dict('records')
        save_data(MONTHLY_DATA_PATH, data)
        return {
            "message": "Monthly data uploaded successfully",
            "records_processed": len(data),
            "date_range": {
                "start": data[0]['date'] if data else None,
                "end": data[-1]['date'] if data else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
@app.get("/api/daily-data")
async def get_daily_data(limit: int = 60):
    ensure_dependencies()
    try:
        data = load_data(DAILY_DATA_PATH)
        limited_data = data[-limit:] if len(data) > limit else data
        return [{
            'date': row['date'],
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
            'high_prev_close_diff': row.get('high_prev_close_diff'),
            'rsi': row.get('rsi'),
            'macd': {
                'line': row.get('macd_line'),
                'signal': row.get('macd_signal'),
                'hist': row.get('macd_hist')
            }
        } for row in limited_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
@app.get("/api/monthly-data")
async def get_monthly_data():
    ensure_dependencies()
    try:
        data = load_data(MONTHLY_DATA_PATH)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
@app.get("/api/stats")
async def get_daily_stats():
    ensure_dependencies()
    try:
        data = load_data(DAILY_DATA_PATH)
        if not data:
            return {
                "total_records": 0,
                "date_range": {"start": None, "end": None},
                "latest_close": None,
                "latest_rsi": None
            }
        return {
            "total_records": len(data),
            "date_range": {
                "start": data[0]['date'],
                "end": data[-1]['date']
            },
            "latest_close": data[-1].get('close'),
            "latest_rsi": data[-1].get('rsi')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
@app.get("/api/monthly-stats")
async def get_monthly_stats():
    ensure_dependencies()
    try:
        data = load_data(MONTHLY_DATA_PATH)
        if not data:
            return {
                "total_records": 0,
                "date_range": {"start": None, "end": None}
            }
        return {
            "total_records": len(data),
            "date_range": {
                "start": data[0]['date'],
                "end": data[-1]['date']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
handler = Mangum(app)
