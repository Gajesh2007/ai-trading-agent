import requests
import os
import time
import logging
from src.config_loader import CONFIG

class TAAPIClient:
    def __init__(self):
        self.api_key = CONFIG["taapi_api_key"]
        self.base_url = "https://api.taapi.io/"

    def _get_with_retry(self, url, params, retries=3, backoff=0.5):
        """GET with exponential backoff retry."""
        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                return resp.json()
            except requests.HTTPError as e:
                if e.response.status_code == 429:  # Rate Limit
                    logging.warning("TAAPI Rate Limit (429), waiting 15s")
                    time.sleep(15)
                    continue
                if e.response.status_code >= 500 and attempt < retries - 1:
                    wait = backoff * (2 ** attempt)
                    logging.warning(f"TAAPI {e.response.status_code}, retrying in {wait}s")
                    time.sleep(wait)
                else:
                    raise
            except requests.Timeout as e:
                if attempt < retries - 1:
                    wait = backoff * (2 ** attempt)
                    logging.warning(f"TAAPI timeout, retrying in {wait}s")
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Max retries exceeded")

    def get_indicators(self, asset, interval):
        params = {
            "secret": self.api_key,
            "exchange": "binance",
            "symbol": f"{asset}/USDT",
            "interval": interval
        }
        rsi_response = self._get_with_retry(f"{self.base_url}rsi", params)
        time.sleep(4)  
        macd_response = self._get_with_retry(f"{self.base_url}macd", params)
        time.sleep(4) 
        sma_response = self._get_with_retry(f"{self.base_url}sma", params)
        time.sleep(4) 
        ema_response = self._get_with_retry(f"{self.base_url}ema", params)
        time.sleep(4) 
        bbands_response = self._get_with_retry(f"{self.base_url}bbands2", params)  # اصلاح به bbands2
        time.sleep(4)  
        return {
            "rsi": rsi_response.get("value"),
            "macd": macd_response,
            "sma": sma_response.get("value"),
            "ema": ema_response.get("value"),
            "bbands": bbands_response
        }

    def get_historical_indicator(self, indicator, symbol, interval, results=10, params=None):
        base_params = {
            "secret": self.api_key,
            "exchange": "binance",
            "symbol": symbol,
            "interval": interval,
            "results": results
        }
        if params:
            base_params.update(params)
        response = self._get_with_retry(f"{self.base_url}{indicator}", base_params)
        time.sleep(4)
        return response

    def fetch_series(self, indicator: str, symbol: str, interval: str, results: int = 10, params: dict | None = None, value_key: str = "value") -> list:
        """Fetch historical series. TAAPI returns {"value": [array]} for simple indicators or {"valueMACD": [...], ...} for complex ones."""
        try:
            data = self.get_historical_indicator(indicator, symbol, interval, results=results, params=params)
            if isinstance(data, dict):
                # Simple indicators: {"value": [1,2,3]}
                if value_key in data and isinstance(data[value_key], list):
                    return [round(v, 4) if isinstance(v, (int, float)) else v for v in data[value_key]]
                # Error response
                if "error" in data:
                    logging.error(f"TAAPI error for {indicator} {symbol} {interval}: {data.get('error')}")
                    return []
            return []
        except Exception as e:
            logging.error(f"TAAPI fetch_series exception for {indicator}: {e}")
            return []

    def fetch_value(self, indicator: str, symbol: str, interval: str, params: dict | None = None, key: str = "value"):
        """Fetch single value (no results param). TAAPI returns {"value": number}."""
        try:
            base_params = {
                "secret": self.api_key,
                "exchange": "binance",
                "symbol": symbol,
                "interval": interval
            }
            if params:
                base_params.update(params)
            data = self._get_with_retry(f"{self.base_url}{indicator}", base_params)
            time.sleep(4) 
            if isinstance(data, dict):
                val = data.get(key)
                return round(val, 4) if isinstance(val, (int, float)) else val
            return None
        except Exception:
            return None
