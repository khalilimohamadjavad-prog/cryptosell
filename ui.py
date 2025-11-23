import customtkinter as ctk
import threading, time
from tkinter import ttk, messagebox
from chart_viewer import ChartViewer
ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('dark-blue')

class AppUI:
    def __init__(self, scanner, db, telegram_sender):
        self.scanner = scanner
        self.db = db
        self.telegram = telegram_sender
        self.root = ctk.CTk()
        self.root.title('Crypto Short-Term Scanner — Professional')
        self.root.geometry('1100x760')

        # --- top controls ---
        top = ctk.CTkFrame(self.root)
        top.pack(fill='x', padx=12, pady=12)
        ctk.CTkLabel(top, text='Symbols (comma separated | coinGecko id or ticker):').grid(row=0,column=0,sticky='w')
        self.symbols_var = ctk.StringVar(value=','.join(self.scanner.config.get('symbols',[])))
        self.symbols_entry = ctk.CTkEntry(top, textvariable=self.symbols_var, width=640)
        self.symbols_entry.grid(row=0,column=1,sticky='w',padx=8)
        self.scan_btn = ctk.CTkButton(top, text='Scan', command=self.on_scan)
        self.scan_btn.grid(row=0,column=2,padx=8)
        self.reload_btn = ctk.CTkButton(top, text='Reload DB', command=self.reload_table)
        self.reload_btn.grid(row=0,column=3,padx=8)

        ctk.CTkLabel(top, text='Telegram Bot Token:').grid(row=1,column=0,sticky='w', pady=8)
        self.bot_token_entry = ctk.CTkEntry(top, width=420)
        self.bot_token_entry.grid(row=1,column=1,sticky='w',padx=8)
        ctk.CTkLabel(top, text='Chat ID:').grid(row=1,column=2,sticky='w')
        self.chat_id_entry = ctk.CTkEntry(top, width=220)
        self.chat_id_entry.grid(row=1,column=3,sticky='w',padx=8)

        # --- center: table + right panel ---
        center = ctk.CTkFrame(self.root)
        center.pack(fill='both', expand=True, padx=12, pady=(0,12))
        cols = ('id','symbol','type','severity','drop_pct','rsi','btc_div','generated_at')
        self.tree = ttk.Treeview(center, columns=cols, show='headings')
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120)
        self.tree.pack(fill='both', expand=True, side='left')
        self.tree.bind('<Double-1>', self.on_row_double)

        right = ctk.CTkFrame(center, width=340)
        right.pack(side='right', fill='y', padx=8)
        self.view_chart_btn = ctk.CTkButton(right, text='View Chart', command=self.on_view_chart)
        self.view_chart_btn.pack(pady=8, fill='x')
        self.toggle_btn = ctk.CTkButton(right, text='Toggle Theme', command=self.toggle_theme)
        self.toggle_btn.pack(pady=8, fill='x')
        self.clear_btn = ctk.CTkButton(right, text='Clear DB', command=self.clear_db)
        self.clear_btn.pack(pady=8, fill='x')

        self.status = ctk.CTkLabel(self.root, text='Ready')
        self.status.pack(side='bottom', fill='x')
        self.reload_table()

    def run(self):
        self.root.mainloop()

    def set_status(self, t):
        self.status.configure(text=t)
        self.root.update_idletasks()

    def on_scan(self):
        symbols = [s.strip() for s in self.symbols_var.get().split(',') if s.strip()]
        self.scanner.config['symbols'] = symbols
        bot = self.bot_token_entry.get().strip()
        chat = self.chat_id_entry.get().strip()
        if bot and chat:
            self.telegram.set_credentials(bot, chat)
        self.set_status('Scanning...')
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        try:
            results = self.scanner.run_scan()
            self.set_status(f'Found {len(results)} signals. Saving...')
            for r in results:
                self.db.insert_signal(r)
                if self.telegram.is_configured():
                    try:
                        self.telegram.send_message(self.scanner.format_signal_for_telegram(r))
                    except Exception as e:
                        print('Telegram send failed', e)
            time.sleep(0.5)
            self.set_status('Done. Reloading table.')
            self.reload_table()
        except Exception as e:
            messagebox.showerror('Scan error', str(e))
            self.set_status('Error during scan')

    def reload_table(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        rows = self.db.fetch_signals(limit=500)
        for r in rows:
            payload = r.get('payload') or {}
            rsi = payload.get('rsi', '')
            btc_div = payload.get('btc_change_pct', '')
            self.tree.insert('', 'end', values=(r['id'], r['symbol'], r['type'], r['severity'], r['drop_pct'], rsi, btc_div, r['generated_at']))

    def on_row_double(self, event):
        self.on_view_chart()

    def on_view_chart(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo('Select', 'Please select a row')
            return
        item = self.tree.item(sel[0])['values']
        symbol = item[1]
        ChartViewer = ChartViewer = ChartViewer = None
        # open chart
        from chart_viewer import ChartViewer as CV
        CV(symbol).show()

    def toggle_theme(self):
        mode = ctk.get_appearance_mode()
        ctk.set_appearance_mode('light' if mode=='dark' else 'dark')

    def clear_db(self):
        import os
        if messagebox.askyesno('Confirm', 'Clear signals DB?'):
            self.db.conn.execute('DELETE FROM signals')
            self.db.conn.commit()
            self.reload_table()
