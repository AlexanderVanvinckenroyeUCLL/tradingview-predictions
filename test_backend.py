import requests
import sys
from pathlib import Path
API_BASE_URL = "http://localhost:8000"
def test_health_check():
    print(" Testing API health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            print(" API is running")
            return True
        else:
            print(f" API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f" Cannot connect to API at {API_BASE_URL}")
        print("   Make sure the backend is running: cd backend && python main.py")
        return False
def test_upload_csv(csv_file_path):
    print(f"\n Testing CSV upload with: {csv_file_path.name}")
    if not csv_file_path.exists():
        print(f" File not found: {csv_file_path}")
        return False
    try:
        with open(csv_file_path, 'rb') as f:
            files = {'file': (csv_file_path.name, f, 'text/csv')}
            response = requests.post(f"{API_BASE_URL}/api/upload", files=files)
        if response.status_code == 200:
            data = response.json()
            print(f" Upload successful!")
            print(f"   Records processed: {data['records_processed']}")
            print(f"   Date range: {data['date_range']['start']} to {data['date_range']['end']}")
            return True
        else:
            print(f" Upload failed with status {response.status_code}")
            print(f"   Error: {response.json().get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f" Upload error: {str(e)}")
        return False
def test_get_stats():
    print("\n Testing stats endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/stats")
        if response.status_code == 200:
            data = response.json()
            print(f" Stats retrieved successfully")
            print(f"   Total records: {data['total_records']}")
            print(f"   Date range: {data['date_range']['start']} to {data['date_range']['end']}")
            return True
        else:
            print(f" Stats request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f" Stats error: {str(e)}")
        return False
def test_get_daily_data():
    print("\n Testing daily data endpoint (last 10 days)...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/daily-data?limit=10")
        if response.status_code == 200:
            data = response.json()
            print(f" Daily data retrieved successfully")
            print(f"   Records returned: {len(data)}")
            if len(data) > 0:
                first = data[0]
                print(f"\n   Sample record (first day):")
                print(f"   - Date: {first['date']}")
                print(f"   - Close: {first['close']}")
                print(f"   - RSI: {first['rsi']}")
                print(f"   - MACD Line: {first['macd']['line']}")
                print(f"   - MACD Signal: {first['macd']['signal']}")
                print(f"   - MACD Hist: {first['macd']['hist']}")
                required_fields = ['date', 'open', 'high', 'low', 'close', 'volume',
                                 'high_prev_close_diff', 'rsi']
                missing = [f for f in required_fields if first.get(f) is None]
                if missing:
                    print(f"     Missing fields: {missing}")
                else:
                    print(f"    All required fields present")
            return True
        else:
            print(f" Daily data request failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f" Daily data error: {str(e)}")
        return False
def main():
    print("=" * 60)
    print("S&P500 Analysis Backend - Test Suite")
    print("=" * 60)
    if not test_health_check():
        sys.exit(1)
    csv_file = Path(__file__).parent / "data" / "SP_SPX, 1M_db940.csv"
    if not test_upload_csv(csv_file):
        sys.exit(1)
    if not test_get_stats():
        sys.exit(1)
    if not test_get_daily_data():
        sys.exit(1)
    print("\n" + "=" * 60)
    print(" All tests passed!")
    print("=" * 60)
    print("\nYou can now:")
    print("1. Open the frontend: cd frontend && python -m http.server 3000")
    print("2. Visit http://localhost:3000 in your browser")
    print("3. View the dashboard with the uploaded data")
if __name__ == "__main__":
    main()
