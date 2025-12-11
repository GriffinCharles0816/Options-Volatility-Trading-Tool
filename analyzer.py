import tkinter as tk
from tkinter import ttk, messagebox
import threading 
import pandas as pd
import numpy as np
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class IBApp(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)
        self.connected = False
        self.market_data = {}
        self.historical_data = {}

    def error(self, reqId, errorCode, errorString, *args):
        if errorCode == 2176 and "fractional share" in errorString.lower():
            return
        print(f"Error {errorCode}: {errorString}")

    def nextValidId(self, orderId):
        self.connected = True
        print(f"Connected to IBTWS")

    def historical_data(self, reqId, bar):
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []
        self.historical_data[reqId].append({
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        })

    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical data receied for {reqId}")

class VolatilityCrushAnalyzer:

    def __init__(self, root):
        self.root = root
        self.root.title("Volatility Crush Analyzer")
        self.root.geometry("1200X800")

        self.ib_app = IBApp()
        self.connected = False

        self.current_spot = None
        self.current_iv = None
        self.ticker = None

        self.risk_free_rate = 0.5
        self.setup_ui()

    def create_equity_contract(self, symbol):
        contract = Contract()
        contract.symbol = symbol.upper()
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        title_label = ttk.Label(main_frame, 
                                text="Volatility Crush Trade Analyzer",
                                font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        right_frame.columnconfigure(0, weight=1)

        self.setup_connection_section(left_frame, 0)
        self.setup_market_data_section(left_frame, 1)
        self.setup_current_straddle_section(left_frame, 2)
        self.setup_current_greeks_section(left_frame, 3)

        self.setup_scenario_section(right_frame, 0)
        self.setup_pnl_section(right_frame, 1)
        self.setup_new_greeks_section(right_frame, 2)
        self.setup_status_section(right_frame, 3)
    
    def setup_connection_section(self, parent, row):
        conn_frame = ttk.LabelFrame(parent, text="Interactive Brokers Connection", padding="15")
        conn_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        self.host_var = tk.StringVar(value='127.0.0.1')
        ttk.Entry(conn_frame, textvariable=self.host_var, width=15).grid(row=0, column=1, padx=(0, 15), sticky=(tk.W, tk.E))

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, padx=(0, 5), sticky=(tk.W, tk.E))
        self.port_var = tk.StringVar(value='7497')
        ttk.Entry(conn_frame, textvariable=self.port_var, width=10).grid(row=0, column=3, padx=(0, 15), sticky=(tk.W, tk.E))

        button_frame = ttk.Frame(conn_frame)
        button_frame.grid(row=1, column=0, columnspan=4, pady=(10, 0))

        self.connect_btn = ttk.Button(button_frame, text="Connect to IB", command=self.connect_ib)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 10))
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_ib, state='disabled')
        self.disconnect_btn.pack(sode=tk.LEFT)

        self.status_label = ttk.Label(button_frame, text="Disconnected", foreground="red")
        self.status_label.grid(row=2, column=0, columnspan=4, pady=(5, 0))

    def setup_market_data_section(self, parent, row):
        data_frame = ttk.LabelFrame(parent, text="Market Data & Parameters", padding="10")
        data_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        data_frame.columnconfigure(1, weight=1)

        ttk.Label(data_frame, text="Ticker:").grid(row=0, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        ticker_frame = ttk.Frame(data_frame)
        ticker_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 8))
        ticker_frame.columnconfigure(0, weight=1)

        self.ticker_var = tk.StringVar(value="NVDA")
        ttk.Entry(ticker_frame, textvariable=self.ticker_var, widget=12, font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        self.fetch_btn = ttk.Button(ticker_frame, text="Fetch Data", command=self.fetch_market_data, state='disabled')
        self.fetch_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Spot Price
        ttk.Label(data_frame, text='Spot Price:').grid(row=1, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.spot_price_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.spot_price_var, widget=15, font=('Arial', 10, 'bold')).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 8))

        # Strike Price
        ttk.Label(data_frame, text='Strike Price:').grid(row=2, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.strike_price_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.strike_price_var, widget=15, font=('Arial', 10, 'bold')).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 8))

        # Implied Volatility
        ttk.Label(data_frame, text='IV (%):').grid(row=3, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.iv_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.iv_var, widget=15, font=('Arial', 10, 'bold')).grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 8))        

        # Days to Expiry
        ttk.Label(data_frame, text='Days to Expiry:').grid(row=4, column=0, padx=(0, 10), pady=(0, 8), sticky=tk.W)
        self.days_var = tk.StringVar()
        ttk.Entry(data_frame, textvariable=self.days_var, widget=15, font=('Arial', 10, 'bold')).grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 8))

        # Stradle 
        self.price_btn = ttk.Button(data_frame, text="Price Straddle", command=self.price_current_straddle, satate='disabled')
        self.price_btn.grid(row=5, column=0, columnspan=2, padx=(10, 0))

        # Try Adding Strangle

    def setup_current_straddle_section(self, parent, row):
        pricing_frame = ttk.LabelFrame(parent, text="Current Straddle Price", padding="10")
        pricing_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        pricing_frame.columnconfigure(1, weight=1)

        ttk.Label(pricing_frame, text="Call Price:").grid(row=0, column=0, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.call_price_label = ttk.Label(pricing_frame, text="$0.00", font=("Arial", 11, "bold"), foreground='green')
        self.call_price_label.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))

        ttk.Label(pricing_frame, text="Put Price:").grid(row=1, column=0, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.put_price_label = ttk.Label(pricing_frame, text="$0.00", font=("Arial", 11, "bold"), foreground='red')
        self.put_price_label.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))

        separator = ttk.Separator(pricing_frame, orient='horizontal')
        separator.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)

        ttk.Label(pricing_frame, text="Straddle Price:").grid(row=3, column=0, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.straddle_price_label = ttk.Label(pricing_frame, text="$0.00", font=("Arial", 14, "bold"), foreground='blue')
        self.straddle_price_label.grid(row=3, column=1, sticky=tk.W, pady=(0, 5))   

    def setup_current_greeks_section(self, parent, row):
        greeks_frame = ttk.LabelFrame(parent, text="Current Greeks", padding="10")
        greeks_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        greeks_frame.columnconfigure(1, weight=1)
        greeks_frame.columnconfigure(3, weight=1)

        ttk.Label(greeks_frame, text="Delta (δ):").grid(row=0, column=0, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.delta_label = ttk.Label(greeks_frame, text="$0.00", font=("Arial", 10, "bold"))
        self.delta_label.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))  

        ttk.Label(greeks_frame, text="Gamma (γ):").grid(row=0, column=2, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.gamma_label = ttk.Label(greeks_frame, text="$0.00", font=("Arial", 10, "bold"))
        self.gamma_label.grid(row=0, column=3, sticky=tk.W, pady=(0, 5))  

        ttk.Label(greeks_frame, text="Vega (v):").grid(row=1, column=0, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.vega_label = ttk.Label(greeks_frame, text="$0.00", font=("Arial", 10, "bold"))
        self.vega_label.grid(row=1, column=1, sticky=tk.W, pady=(0, 5))  

        ttk.Label(greeks_frame, text="Theta (θ):").grid(row=1, column=2, padx=(0, 10), pady=(0, 5), sticky=tk.W)
        self.theta_label = ttk.Label(greeks_frame, text="$0.00", font=("Arial", 10, "bold"))
        self.theta_label.grid(row=1, column=3, sticky=tk.W, pady=(0, 5))  



