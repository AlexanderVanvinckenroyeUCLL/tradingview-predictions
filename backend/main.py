from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import sqlite3
from datetime import datetime
import io
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="S&P500 Analysis API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DB_PATH = "sp500_data.db"
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
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
    logger.info("Database initialized")
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
    macd_signal = calculate_ema(macd_line, signal)
    macd_hist = macd_line - macd_signal
    return {
        'line': macd_line,
        'signal': macd_signal,
        'hist': macd_hist
    }
def process_monthly_csv_data(csv_content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(csv_content))
        logger.info(f"Monthly CSV loaded with {len(df)} rows and columns: {list(df.columns)}")
        df.columns = df.columns.str.lower().str.strip()
        required_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        df = df[required_cols].copy()
        df['time'] = pd.to_datetime(df['time'], unit='s', errors='ignore')
        if df['time'].dtype == 'object':
            df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        initial_len = len(df)
        df = df.dropna(subset=['time', 'open', 'high', 'low', 'close'])
        removed = initial_len - len(df)
        if removed > 0:
            logger.info(f"Removed {removed} rows with missing values")
        df = df.rename(columns={'time': 'date'})
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        logger.info(f"Monthly processing complete. Final dataset: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error processing monthly CSV: {str(e)}")
        raise
def process_csv_data(csv_content: bytes) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(csv_content))
        logger.info(f"CSV loaded with {len(df)} rows and columns: {list(df.columns)}")
        df.columns = df.columns.str.lower().str.strip()
        required_cols = ['time', 'open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        df = df[required_cols].copy()
        df['time'] = pd.to_datetime(df['time'], unit='s', errors='ignore')
        if df['time'].dtype == 'object':
            df['time'] = pd.to_datetime(df['time'])
        df = df.sort_values('time').reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        initial_len = len(df)
        df = df.dropna(subset=['time', 'open', 'high', 'low', 'close'])
        removed = initial_len - len(df)
        if removed > 0:
            logger.info(f"Removed {removed} rows with missing values")
        df['high_prev_close_diff'] = df['high'] - df['close'].shift(1)
        df['rsi'] = calculate_rsi(df['close'], period=14)
        macd_values = calculate_macd(df['close'], fast=12, slow=26, signal=9)
        df['macd_line'] = macd_values['line']
        df['macd_signal'] = macd_values['signal']
        df['macd_hist'] = macd_values['hist']
        df = df.rename(columns={'time': 'date'})
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        logger.info(f"Processing complete. Final dataset: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error processing CSV: {str(e)}")
        raise
def save_to_db(df: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    try:
        df.to_sql('daily_data', conn, if_exists='replace', index=False)
        conn.commit()
        logger.info(f"Saved {len(df)} records to daily_data table")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving to database: {str(e)}")
        raise
    finally:
        conn.close()
def save_monthly_to_db(df: pd.DataFrame):
    conn = sqlite3.connect(DB_PATH)
    try:
        df[['date', 'open', 'high', 'low', 'close', 'volume']].to_sql(
            'monthly_data', conn, if_exists='replace', index=False
        )
        conn.commit()
        logger.info(f"Saved {len(df)} records to monthly_data table")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error saving monthly data to database: {str(e)}")
        raise
    finally:
        conn.close()
@app.on_event("startup")
async def startup_event():
    init_db()
@app.get("/")
async def root():
    return {"status": "ok", "message": "S&P500 Analysis API"}
@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        content = await file.read()
        df = process_csv_data(content)
        save_to_db(df)
        return {
            "status": "success",
            "message": "CSV uploaded and processed successfully",
            "records_processed": len(df),
            "date_range": {
                "start": df['date'].min(),
                "end": df['date'].max()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
@app.get("/api/daily-data")
async def get_daily_data(limit: int = 60) -> List[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daily_data")
        count = cursor.fetchone()[0]
        if count == 0:
            conn.close()
            return []
        query = """
            SELECT
                date,
                open,
                high,
                low,
                close,
                volume,
                high_prev_close_diff,
                rsi,
                macd_line,
                macd_signal,
                macd_hist
            FROM daily_data
            ORDER BY date DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "date": row[0],
                "open": round(row[1], 2) if row[1] is not None else None,
                "high": round(row[2], 2) if row[2] is not None else None,
                "low": round(row[3], 2) if row[3] is not None else None,
                "close": round(row[4], 2) if row[4] is not None else None,
                "volume": int(row[5]) if row[5] is not None else None,
                "high_prev_close_diff": round(row[6], 2) if row[6] is not None else None,
                "rsi": round(row[7], 2) if row[7] is not None else None,
                "macd": {
                    "line": round(row[8], 2) if row[8] is not None else None,
                    "signal": round(row[9], 2) if row[9] is not None else None,
                    "hist": round(row[10], 2) if row[10] is not None else None
                }
            })
        result.reverse()
        conn.close()
        logger.info(f"Returned {len(result)} records")
        return result
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/stats")
async def get_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM daily_data")
        row = cursor.fetchone()
        conn.close()
        return {
            "total_records": row[0],
            "date_range": {
                "start": row[1],
                "end": row[2]
            }
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/upload-monthly")
async def upload_monthly_csv(file: UploadFile = File(...)):
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")
        content = await file.read()
        df = process_monthly_csv_data(content)
        save_monthly_to_db(df)
        return {
            "status": "success",
            "message": "Monthly CSV uploaded successfully",
            "records_processed": len(df),
            "date_range": {
                "start": df['date'].min(),
                "end": df['date'].max()
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Monthly upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
@app.get("/api/monthly-data")
async def get_monthly_data(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM monthly_data")
        count = cursor.fetchone()[0]
        if count == 0:
            conn.close()
            return []
        if limit:
            query = """
                SELECT date, open, high, low, close, volume
                FROM monthly_data
                ORDER BY date DESC
                LIMIT ?
            """
            cursor.execute(query, (limit,))
        else:
            query = """
                SELECT date, open, high, low, close, volume
                FROM monthly_data
                ORDER BY date DESC
            """
            cursor.execute(query)
        rows = cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "date": row[0],
                "open": round(row[1], 2) if row[1] is not None else None,
                "high": round(row[2], 2) if row[2] is not None else None,
                "low": round(row[3], 2) if row[3] is not None else None,
                "close": round(row[4], 2) if row[4] is not None else None,
                "volume": int(row[5]) if row[5] is not None else None
            })
        result.reverse()
        conn.close()
        logger.info(f"Returned {len(result)} monthly records")
        return result
    except Exception as e:
        logger.error(f"Error fetching monthly data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/monthly-stats")
async def get_monthly_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM monthly_data")
        row = cursor.fetchone()
        conn.close()
        return {
            "total_records": row[0],
            "date_range": {
                "start": row[1],
                "end": row[2]
            }
        }
    except Exception as e:
        logger.error(f"Error fetching monthly stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
