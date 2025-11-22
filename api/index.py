from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime
import io
import sys
import traceback
import csv
import math

print("Booting api/index.py (pure python, no pandas/numpy)", sys.version, file=sys.stderr)
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
def load_data(path: str) -> List[Dict]:
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return []
def save_data(path: str, data: List[Dict]):
    with open(path, 'w') as f:
        json.dump(data, f)
def parse_time(value: str) -> datetime:
    # Supports epoch seconds or ISO date string
    try:
        # integer or float epoch
        num = float(value)
        return datetime.fromtimestamp(num)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(value)
    except Exception:
        # fallback to pandas-like format with Z stripped
        if isinstance(value, str) and value.endswith("Z"):
            return datetime.fromisoformat(value.rstrip("Z"))
        raise


def read_csv_rows(contents: bytes) -> List[Dict[str, Any]]:
    text = contents.decode('utf-8', errors='replace')
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        rows.append(row)
    return rows


def to_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except Exception:
        return None


def process_daily_data(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Parse and sort by time
    parsed = []
    for r in rows:
        try:
            t = parse_time(str(r.get("time", "")).strip())
        except Exception:
            continue
        parsed.append({
            "time": t,
            "open": to_float(r.get("open")),
            "high": to_float(r.get("high")),
            "low": to_float(r.get("low")),
            "close": to_float(r.get("close")),
            "volume": to_float(r.get("volume")),
        })
    parsed = [p for p in parsed if None not in (p["open"], p["high"], p["low"], p["close"], p["volume"])]
    parsed.sort(key=lambda x: x["time"])

    closes = [p["close"] for p in parsed]

    def calculate_rsi(values: List[float], period: int = 14) -> List[Optional[float]]:
        if len(values) < period + 1:
            return [None] * len(values)
        deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
        gains = [max(d, 0) for d in deltas]
        losses = [-min(d, 0) for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        rsi_values = [None] * period

        for i in range(period, len(values)):
            gain = gains[i - 1]
            loss = losses[i - 1]
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            rsi_values.append(rsi)
        return rsi_values

    def ema(values: List[float], period: int) -> List[float]:
        if not values:
            return []
        k = 2 / (period + 1)
        ema_vals = [values[0]]
        for v in values[1:]:
            ema_vals.append(v * k + ema_vals[-1] * (1 - k))
        return ema_vals

    def calculate_macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9):
        if not values:
            return {"line": [], "signal": [], "hist": []}
        ema_fast = ema(values, fast)
        ema_slow = ema(values, slow)
        # align lengths
        min_len = min(len(ema_fast), len(ema_slow))
        ema_fast = ema_fast[-min_len:]
        ema_slow = ema_slow[-min_len:]
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = ema(macd_line, signal)
        hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
        # pad to original length with None at start
        pad_len = len(values) - len(macd_line)
        macd_line = [None] * pad_len + macd_line
        signal_line = [None] * (len(values) - len(signal_line)) + signal_line
        hist = [None] * (len(values) - len(hist)) + hist
        return {"line": macd_line, "signal": signal_line, "hist": hist}

    rsi_vals = calculate_rsi(closes)
    macd_vals = calculate_macd(closes)

    result = []
    for idx, row in enumerate(parsed):
        prev_close = parsed[idx - 1]["close"] if idx > 0 else None
        result.append({
            "date": row["time"].strftime("%Y-%m-%d"),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "high_prev_close_diff": row["high"] - prev_close if prev_close is not None else None,
            "rsi": rsi_vals[idx] if idx < len(rsi_vals) else None,
            "macd_line": macd_vals["line"][idx] if idx < len(macd_vals["line"]) else None,
            "macd_signal": macd_vals["signal"][idx] if idx < len(macd_vals["signal"]) else None,
            "macd_hist": macd_vals["hist"][idx] if idx < len(macd_vals["hist"]) else None,
        })
    return result


def process_monthly_data(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    parsed = []
    for r in rows:
        try:
            t = parse_time(str(r.get("time", "")).strip())
        except Exception:
            continue
        parsed.append({
            "time": t,
            "open": to_float(r.get("open")),
            "high": to_float(r.get("high")),
            "low": to_float(r.get("low")),
            "close": to_float(r.get("close")),
            "volume": to_float(r.get("volume")),
        })
    parsed = [p for p in parsed if None not in (p["open"], p["high"], p["low"], p["close"], p["volume"])]
    parsed.sort(key=lambda x: x["time"])

    result = []
    for row in parsed:
        result.append({
            "date": row["time"].strftime("%Y-%m-%d"),
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
        })
    return result
@app.get("/")
async def root():
    return {"message": "S&P500 Analysis API", "status": "running"}
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "python_version": sys.version,
        "pandas_used": False,
        "numpy_used": False,
    }


@app.get("/api/debug-env")
async def debug_env():
    return {
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "files": os.listdir("."),
        "pandas_used": False,
        "numpy_used": False,
    }
@app.post("/api/upload")
async def upload_daily_data(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        rows = read_csv_rows(contents)
        required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        if not rows or not all(col in rows[0] for col in required_columns):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        data = process_daily_data(rows)
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
        print("Error in upload_monthly_data:", e, file=sys.stderr)
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
@app.post("/api/upload-monthly")
async def upload_monthly_data(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        rows = read_csv_rows(contents)
        required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        if not rows or not all(col in rows[0] for col in required_columns):
            raise HTTPException(
                status_code=400,
                detail=f"CSV must contain columns: {', '.join(required_columns)}"
            )
        data = process_monthly_data(rows)
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
        print("Error in upload_daily_data:", e, file=sys.stderr)
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
@app.get("/api/daily-data")
async def get_daily_data(limit: int = 60):
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
        print("Error in get_daily_data:", e, file=sys.stderr)
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
@app.get("/api/monthly-data")
async def get_monthly_data():
    try:
        data = load_data(MONTHLY_DATA_PATH)
        return data
    except Exception as e:
        print("Error in get_monthly_data:", e, file=sys.stderr)
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")
@app.get("/api/stats")
async def get_daily_stats():
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
        print("Error in get_daily_stats:", e, file=sys.stderr)
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
@app.get("/api/monthly-stats")
async def get_monthly_stats():
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
        print("Error in get_monthly_stats:", e, file=sys.stderr)
        traceback.print_exception(type(e), e, e.__traceback__, file=sys.stderr)
        sys.stderr.flush()
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")
