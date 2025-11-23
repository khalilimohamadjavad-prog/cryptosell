import requests, time, os
import pandas as pd
import numpy as np
from datetime import datetime

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(alpha=1/period, adjust=False).mean()
    ma_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

class Scanner:
    COINGECKO = 'https://api.coingecko.com/api/v3'
    CRYPTOCOMPARE = 'https://min-api.cryptocompare.com/data'
    def __init__(self, db, config=None):
        self.db = db
        self.config = config or {}
        self.config.setdefault('symbols',['bitcoin','ethereum','solana','ripple'])
        self.config.setdefault('drop_threshold_pct',15)
        self.config.setdefault('lookback_days',7)
        self.cc_key = os.environ.get('CRYPTOCOMPARE_KEY','')
        self.use_cc = bool(self.cc_key) or self.config.get('use_cryptocompare', False)
        self._coin_list = None
        self._coin_ts = 0

    def _refresh_coin_list(self):
        if self._coin_list and (time.time()-self._coin_ts) < 24*3600:
            return
        try:
            r = requests.get(f"{self.COINGECKO}/coins/list", timeout=12)
            r.raise_for_status()
            self._coin_list = r.json()
            self._coin_ts = time.time()
        except Exception:
            self._coin_list = []

    def _map_symbol(self, s):
        self._refresh_coin_list()
        if not self._coin_list:
            return None
        s = s.lower()
        for c in self._coin_list:
            if c['id'].lower() == s or c.get('symbol','').lower() == s:
                return c['id']
        return None

    def _get_ohlc_cc(self, fsym, limit=500):
        try:
            url = f"{self.CRYPTOCOMPARE}/v2/histohour?fsym={fsym}&tsym=USD&limit={limit}&api_key={self.cc_key}"
            r = requests.get(url, timeout=12)
            r.raise_for_status()
            data = r.json()
            if data.get('Response')!='Success':
                return None
            arr = data.get('Data',{}).get('Data',[])
            rows=[]
            for c in arr:
                rows.append({'Date': pd.to_datetime(c['time'], unit='s'), 'Open': c['open'], 'High': c['high'], 'Low': c['low'], 'Close': c['close']})
            df = pd.DataFrame(rows).set_index('Date')
            return df
        except Exception:
            return None

    def _get_ohlc_cg(self, coin_id, days=7):
        try:
            url = f"{self.COINGECKO}/coins/{coin_id}/ohlc?vs_currency=usd&days={days}"
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            arr = r.json()
            rows=[]
            for c in arr:
                rows.append({'Date': pd.to_datetime(c[0], unit='ms'), 'Open': float(c[1]), 'High': float(c[2]), 'Low': float(c[3]), 'Close': float(c[4])})
            df = pd.DataFrame(rows).set_index('Date')
            return df
        except Exception:
            return None

    def _get_df(self, symbol):
        if self.use_cc and self.cc_key:
            df = self._get_ohlc_cc(symbol.upper(), limit=500)
            if df is not None and not df.empty:
                return df
        coin_id = self._map_symbol(symbol)
        if coin_id:
            days = max(3, min(90, int(self.config.get('lookback_days',7))))
            return self._get_ohlc_cg(coin_id, days=days)
        return None

    def _is_new_high_and_drop(self, df, within_days=3, threshold=15):
        if df is None or df.empty:
            return None
        now = df.index.max()
        cutoff = now - pd.Timedelta(days=within_days)
        recent = df[df.index >= cutoff]
        if recent.empty:
            return None
        peak_idx = recent['High'].idxmax()
        peak_price = float(recent.loc[peak_idx]['High'])
        current = float(df.iloc[-1]['Close'])
        drop_pct = (peak_price - current)/peak_price*100.0
        if drop_pct >= threshold:
            # compute RSI on close
            rs = rsi(df['Close'].astype(float))
            latest_rsi = float(rs.iloc[-1]) if not rs.empty else None
            return {'peak_time': peak_idx.isoformat(), 'peak_price': peak_price, 'current_price': current, 'drop_pct': round(drop_pct,2), 'rsi': round(latest_rsi,2) if latest_rsi else None}
        return None

    def run_scan(self):
        results=[]
        symbols = self.config.get('symbols',[])
        threshold = self.config.get('drop_threshold_pct',15)
        for s in symbols:
            try:
                df = self._get_df(s)
                if df is None:
                    self.db.insert_log('WARN', f'No data for {s}')
                    continue
                check = self._is_new_high_and_drop(df, within_days=3, threshold=threshold)
                if check:
                    # compare with BTC
                    btc_df = self._get_df('bitcoin')
                    btc_change = None
                    if btc_df is not None and not btc_df.empty:
                        btc_after = btc_df[btc_df.index >= pd.to_datetime(check['peak_time'])]
                        if not btc_after.empty:
                            btc_peak_close = float(btc_after.iloc[0]['Close'])
                            btc_now = float(btc_df.iloc[-1]['Close'])
                            btc_change = (btc_now - btc_peak_close)/btc_peak_close*100.0
                    payload = check
                    payload['btc_change_pct'] = round(btc_change or 0.0,2)
                    sig = {'symbol': s, 'type':'new-high-drop', 'severity':'high' if check['drop_pct']>=25 else 'medium', 'drop_pct': check['drop_pct'], 'payload': payload, 'generated_at': datetime.utcnow().isoformat()}
                    results.append(sig)
            except Exception as e:
                self.db.insert_log('ERROR', f'Scan error {s}: {e}')
                continue
        return results

    def format_signal_for_telegram(self, sig):
        p = sig.get('payload',{})
        txt = f"🚨 سیگنال: {sig['symbol']}\n"
        txt += f"نوع: {sig['type']}\n"
        txt += f"شدت: {sig['severity']}\n\n"
        txt += f"قله: {p.get('peak_time')} — {p.get('peak_price')}\n"
        txt += f"قیمت فعلی: {p.get('current_price')}\n"
        txt += f"ریزش از قله: {p.get('drop_pct')}%\n"
        txt += f"RSI: {p.get('rsi')}\n"
        txt += f"مقایسه با BTC: {p.get('btc_change_pct')}%\n\n"
        txt += 'تحلیل: سیگنال خودکار (تحقیق کنید قبل از معامله)\n'
        return txt
