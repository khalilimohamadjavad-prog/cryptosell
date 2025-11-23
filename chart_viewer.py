import mplfinance as mpf
import pandas as pd
import requests
from datetime import datetime
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import customtkinter as ctk
from tkinter import Toplevel, messagebox

class ChartViewer:
    COINGECKO='https://api.coingecko.com/api/v3'
    CRYPTOCOMPARE='https://min-api.cryptocompare.com/data'
    def __init__(self, symbol):
        self.symbol = symbol
    def _get_df(self, symbol):
        # try cryptocompare
        import os
        cc = os.environ.get('CRYPTOCOMPARE_KEY','')
        if cc:
            try:
                url = f"{self.CRYPTOCOMPARE}/v2/histohour?fsym={symbol.upper()}&tsym=USD&limit=500&api_key={cc}"
                r = requests.get(url, timeout=12)
                r.raise_for_status()
                data = r.json()
                arr = data.get('Data',{}).get('Data',[])
                rows=[]
                for c in arr:
                    rows.append({'Date': pd.to_datetime(c['time'], unit='s'), 'Open': c['open'], 'High': c['high'], 'Low': c['low'], 'Close': c['close'], 'Volume': c.get('volumefrom',0)})
                return pd.DataFrame(rows).set_index('Date')
            except Exception:
                pass
        # fallback to coingecko by mapping id
        try:
            list_r = requests.get(f"{self.COINGECKO}/coins/list", timeout=12)
            list_r.raise_for_status()
            coin_list = list_r.json()
            sid=None
            s=symbol.lower()
            for c in coin_list:
                if c['id'].lower()==s or c.get('symbol','').lower()==s:
                    sid=c['id']; break
            if sid:
                r = requests.get(f"{self.COINGECKO}/coins/{sid}/ohlc?vs_currency=usd&days=7", timeout=15)
                r.raise_for_status()
                arr=r.json(); rows=[]
                for c in arr:
                    rows.append({'Date': pd.to_datetime(c[0], unit='ms'), 'Open': float(c[1]), 'High': float(c[2]), 'Low': float(c[3]), 'Close': float(c[4]), 'Volume': None})
                return pd.DataFrame(rows).set_index('Date')
        except Exception as e:
            print('chart error', e)
        return None
    def show(self):
        df = self._get_df(self.symbol)
        if df is None or df.empty:
            messagebox.showinfo('No data', 'Could not fetch chart data for ' + self.symbol)
            return
        fig, axlist = mpf.plot(df, type='candle', volume=True, returnfig=True, figscale=1.2)
        win = Toplevel(); win.title('Candle - '+self.symbol)
        canvas = FigureCanvasTkAgg(fig, master=win); canvas.draw(); canvas.get_tk_widget().pack(fill='both', expand=True)
