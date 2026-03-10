from flask import Flask, render_template, jsonify
from data_loader import GoldDataLoader
from features import GoldFeatures
from engine import GoldEngine
from risk_mgmt import RiskManagement
from quant_math import QuantMath
import pandas as pd
import numpy as np
import threading
import time

app = Flask(__name__)

# ── BAŞLANGIÇ CACHE'İ ──────────────────────────────
cached_data = {
    "ons": {"price": 0.0, "prev": 0.0},
    "gram": {"price": 0.0, "prev": 0.0},
    "df": [],
    "metrics": {
        "RSI": 50.0, "MACD": 0.0, "MACD_Hist": 0.0, "MACD_Signal": 0.0,
        "BB_Upper": 0.0, "BB_Mid": 0.0, "BB_Lower": 0.0, "BB_Pct": 0.5,
        "ATR": 0.0, "Williams_R": -50.0, "CCI": 0.0,
        "Stoch_K": 50.0, "Stoch_D": 50.0,
        "Z_Score": 0.0, "Hurst": 0.5, "Half_Life": 0.0,
        "Volatility": 0.0, "GARCH_Vol": 0.0,
        "Momentum_5": 0.0, "Momentum_20": 0.0, "Momentum_60": 0.0,
        "Sharpe": 0.0, "Sortino": 0.0, "MaxDD": 0.0,
        "Rolling_Sharpe": 0.0,
        "Regime": "YÜKLENİYOR", "Vol_Regime": "NORMAL", "Signal": "BEKLE",
        "Signal_Momentum": "BEKLE", "Signal_MeanRev": "BEKLE",
        "Signal_Trend": "BEKLE", "Signal_Combined": "BEKLE",
        "SMA_20": 0.0, "SMA_50": 0.0, "SMA_200": 0.0,
        "Fib_0236": 0.0, "Fib_0382": 0.0, "Fib_0500": 0.0,
        "Fib_0618": 0.0, "Fib_0786": 0.0,
        "Autocorr_Lag1": 0.0, "Rolling_Skew": 0.0, "Rolling_Kurt": 0.0,
    },
    "risk": {
        "VAR_95": 0.0, "VAR_99": 0.0, "CVaR_95": 0.0,
        "Sharpe": 0.0, "Sortino": 0.0, "MaxDD": 0.0, "Calmar": 0.0,
        "Monte_Carlo_30d": 0.0, "Monte_Carlo_90d": 0.0,
        "Win_Rate": 0.0, "Profit_Factor": 0.0, "Expectancy": 0.0,
        "Kelly_F": 0.0, "Volatility_Annual": 0.0,
        "Hurst": 0.5,
    },
    "ai": {
        "RL_Status": "Başlatılıyor...", "RL_Epsilon": 1.0,
        "Patterns": "Analiz bekleniyor...", "Sentiment": 0.0,
        "Memory_Size": 0, "LT_Memory_Size": 0,
        "LSTM_Status": "Simüle", "Transformer_Status": "Simüle",
    },
    "portfolio": {
        "Kelly_F": 0.0, "Risk_Parity_Weight": 0.5,
        "Optimal_Size": 0.0, "Max_Leverage": 1.0,
        "Efficient_Frontier_Sharpe": 0.0,
    },
    "macro": {
        "CPI": 250.0, "Interest_Rate": 5.25, "M2": 21200.0,
        "Sentiment_Score": 0.0,
    },
    "news": [],
    "robot": {
        "action": "BEKLE", "tp": 0.0, "sl": 0.0, "prob_win": 50.0,
        "prob_bull": 50.0, "prob_bear": 50.0
    },
    "last_update": 0
}

def safe_v(val, d=0.0):
    """Güvenli float dönüşümü"""
    try:
        v = float(val)
        return round(v, 6) if np.isfinite(v) else d
    except:
        return d

def safe_str(val, d="N/A"):
    try:
        return str(val) if val else d
    except:
        return d


def update_data_loop():
    loader = GoldDataLoader()
    features = GoldFeatures()
    engine = GoldEngine()
    rm = RiskManagement()

    last_full_update = 0
    df = None
    news = []

    while True:
        try:
            now = time.time()
            
            # --- Ağır İşlemler (Sadece 1 Saatte Bir Çalışır) ---
            if df is None or (now - last_full_update) > 3600:
                print("\n>>> [SİSTEM] Tarihsel Özellikler Yeni Baştan Hesaplanıyor (yfinance)...", flush=True)
                new_df = loader.fetch_gold_data(period="2y")
                news = loader.fetch_news()
                loader.fetch_macro_indicators()

                if new_df is not None and len(new_df) >= 20:
                    df = features.add_technical_indicators(new_df)
                    df = features.add_advanced_features(df)
                    df = features.add_fibonacci_levels(df)
                    df = features.add_volatility_regime(df)
                    df = features.add_market_regime(df)
                    df = features.add_strategy_signals(df)
                    df = features.add_econometric_features(df)
                    last_full_update = now
                else:
                    print("!!! Veri yetersiz, eski tablo tutuluyor.", flush=True)

            if df is None or len(df) < 20:
                time.sleep(30)
                continue

            last = df.iloc[-1]
            returns = df['Log_Return'].dropna()

            # --- Canlı Fiyat Çekimi (Saniyede Bir Çalışabilir - Rate Limit Korumalı) ---
            import requests
            h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            
            try:
                r1 = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d', headers=h, timeout=5)
                ons_price = r1.json()['chart']['result'][0]['meta']['regularMarketPrice']
            except Exception:
                ons_price = safe_v(last.get('Gold_USD', df['Gold_USD'].iloc[-1]))
                
            try:
                r2 = requests.get('https://query1.finance.yahoo.com/v8/finance/chart/USDTRY=X?interval=1m&range=1d', headers=h, timeout=5)
                usdtry = r2.json()['chart']['result'][0]['meta']['regularMarketPrice']
            except Exception:
                usdtry = safe_v(df['USD_TRY'].iloc[-1]) if 'USD_TRY' in df.columns else 35.0
                
            gram_price = (ons_price / 31.1034768) * usdtry

            prev_ons = safe_v(df['Gold_USD'].iloc[-2]) if len(df) > 1 else ons_price
            prev_gram = safe_v(df['Gram_Gold'].iloc[-2]) if len(df) > 1 else gram_price

            # 4. YZ
            sentiment = safe_v(engine.get_sentiment(news))
            rl_status = engine.run_self_learning_loop()
            patterns = engine.memory.extract_semantic_patterns()

            # 5. Risk
            perf = rm.calculate_performance_metrics(returns) if len(returns) > 20 else {}
            mc_30 = safe_v(rm.monte_carlo_stress_test(ons_price, days=30))
            mc_90 = safe_v(rm.monte_carlo_stress_test(ons_price, days=90))
            var_95 = safe_v(QuantMath.calculate_var(returns, 0.95))
            var_99 = safe_v(QuantMath.calculate_var(returns, 0.99))
            cvar_95 = safe_v(QuantMath.calculate_cvar(returns, 0.95))

            # Win Rate & Profit Factor
            pos_returns = returns[returns > 0]
            neg_returns = returns[returns < 0]
            win_rate = safe_v(len(pos_returns) / len(returns) * 100 if len(returns) > 0 else 0)
            profit_factor = safe_v(pos_returns.sum() / abs(neg_returns.sum()) if len(neg_returns) > 0 and neg_returns.sum() != 0 else 0)
            expectancy = safe_v(returns.mean() * 100)

            # Calmar Ratio
            sharpe = safe_v(perf.get('Sharpe', 0))
            maxdd = safe_v(perf.get('Max_Drawdown', 0))
            calmar = safe_v(sharpe / abs(maxdd) if maxdd != 0 else 0)

            # Kelly & Portfolio
            kelly_f = safe_v(QuantMath.kelly_criterion(win_rate/100, max(profit_factor, 0.1)))
            volatility_annual = safe_v(returns.std() * np.sqrt(252))

            # 6. Sinyal ve Karar Robotu
            z_score_val = safe_v(last.get('Z_Score', 0))
            combined_signal = safe_str(last.get('Signal_Combined', 'BEKLE'))
            signal = 'AL' if z_score_val < -1.5 or combined_signal == 'AL' else 'SAT' if z_score_val > 1.5 or combined_signal == 'SAT' else 'BEKLE'
            
            # Basit Robot Tahmini
            bull_prob = 50 + (safe_v(last.get('Momentum_20', 0)) * 500) - (z_score_val * 10)
            bull_prob = max(10, min(90, bull_prob))
            bear_prob = 100 - bull_prob
            
            vol_atr = safe_v(last.get('ATR', ons_price * 0.01))
            tp = ons_price + (vol_atr * 2) if signal == 'AL' else ons_price - (vol_atr * 2)
            sl = ons_price - (vol_atr * 1.5) if signal == 'AL' else ons_price + (vol_atr * 1.5)

            # 7. Grafik Verisi
            df_disp = df.reset_index()
            date_col = [c for c in df_disp.columns if 'date' in c.lower() or c == df_disp.columns[0]][0]
            df_disp[date_col] = pd.to_datetime(df_disp[date_col]).dt.strftime('%Y-%m-%d')

            records = []
            for _, row in df_disp.tail(250).iterrows():
                records.append({
                    'Date': row[date_col],
                    'Gram_Gold': safe_v(row.get('Gram_Gold', 0)),
                    'Gold_USD': safe_v(row.get('Gold_USD', 0)),
                    'RSI': safe_v(row.get('RSI', 50)),
                    'MACD': safe_v(row.get('MACD', 0)),
                    'MACD_Hist': safe_v(row.get('MACD_Hist', 0)),
                    'MACD_Signal': safe_v(row.get('MACD_Signal', 0)),
                    'BB_Upper': safe_v(row.get('BB_Upper', 0)),
                    'BB_Mid': safe_v(row.get('BB_Mid', 0)),
                    'BB_Lower': safe_v(row.get('BB_Lower', 0)),
                    'Volatility': safe_v(row.get('Volatility', 0)),
                    'Z_Score': safe_v(row.get('Z_Score', 0)),
                    'Momentum_20': safe_v(row.get('Momentum_20', 0)),
                    'Volume': safe_v(row.get('Volume', 0)),
                })

            # 8. Cache Güncelle
            cached_data["ons"] = {"price": ons_price, "prev": prev_ons}
            cached_data["gram"] = {"price": gram_price, "prev": prev_gram}
            cached_data["df"] = records

            cached_data["metrics"] = {
                "RSI": safe_v(last.get('RSI', 50), 50),
                "MACD": safe_v(last.get('MACD', 0)),
                "MACD_Hist": safe_v(last.get('MACD_Hist', 0)),
                "MACD_Signal": safe_v(last.get('MACD_Signal', 0)),
                "BB_Upper": safe_v(last.get('BB_Upper', 0)),
                "BB_Mid": safe_v(last.get('BB_Mid', 0)),
                "BB_Lower": safe_v(last.get('BB_Lower', 0)),
                "BB_Pct": safe_v(last.get('BB_Pct', 0.5)),
                "ATR": safe_v(last.get('ATR', 0)),
                "Williams_R": safe_v(last.get('Williams_R', -50)),
                "CCI": safe_v(last.get('CCI', 0)),
                "Stoch_K": safe_v(last.get('Stoch_K', 50)),
                "Stoch_D": safe_v(last.get('Stoch_D', 50)),
                "Z_Score": z_score_val,
                "Hurst": safe_v(last.get('Hurst', 0.5)),
                "Half_Life": safe_v(last.get('Half_Life', 0)),
                "Volatility": safe_v(last.get('Volatility', 0)),
                "GARCH_Vol": safe_v(last.get('GARCH_Vol', 0)),
                "Momentum_5": safe_v(last.get('Momentum_5', 0)),
                "Momentum_20": safe_v(last.get('Momentum_20', 0)),
                "Momentum_60": safe_v(last.get('Momentum_60', 0)),
                "Rolling_Sharpe": safe_v(last.get('Rolling_Sharpe', 0)),
                "Regime": safe_str(last.get('Regime', 'YATAY')),
                "Vol_Regime": safe_str(last.get('Vol_Regime', 'NORMAL')),
                "Signal": signal,
                "Signal_Momentum": safe_str(last.get('Signal_Momentum', 'BEKLE')),
                "Signal_MeanRev": safe_str(last.get('Signal_MeanRev', 'BEKLE')),
                "Signal_Trend": safe_str(last.get('Signal_Trend', 'BEKLE')),
                "Signal_Combined": safe_str(last.get('Signal_Combined', 'BEKLE')),
                "SMA_20": safe_v(last.get('SMA_20', 0)),
                "SMA_50": safe_v(last.get('SMA_50', 0)),
                "SMA_200": safe_v(last.get('SMA_200', 0)),
                "Fib_0236": safe_v(last.get('Fib_0236', 0)),
                "Fib_0382": safe_v(last.get('Fib_0382', 0)),
                "Fib_0500": safe_v(last.get('Fib_0500', 0)),
                "Fib_0618": safe_v(last.get('Fib_0618', 0)),
                "Fib_0786": safe_v(last.get('Fib_0786', 0)),
                "Autocorr_Lag1": safe_v(last.get('Autocorr_Lag1', 0)),
                "Rolling_Skew": safe_v(last.get('Rolling_Skew', 0)),
                "Rolling_Kurt": safe_v(last.get('Rolling_Kurt', 0)),
                "Price_Pos_52wk": safe_v(last.get('Price_Pos_52wk', 0.5)),
            }

            cached_data["risk"] = {
                "VAR_95": var_95, "VAR_99": var_99, "CVaR_95": cvar_95,
                "Sharpe": sharpe, "Sortino": safe_v(perf.get('Sortino', 0)),
                "MaxDD": safe_v(perf.get('Max_Drawdown', 0) * 100),
                "Calmar": calmar, "Monte_Carlo_30d": mc_30, "Monte_Carlo_90d": mc_90,
                "Win_Rate": win_rate, "Profit_Factor": profit_factor, "Expectancy": expectancy,
                "Kelly_F": kelly_f, "Volatility_Annual": volatility_annual,
                "Hurst": safe_v(last.get('Hurst', 0.5)),
            }

            cached_data["ai"] = {
                "RL_Status": safe_str(rl_status),
                "RL_Epsilon": safe_v(engine.rl_agent.epsilon, 1.0),
                "Patterns": safe_str(patterns),
                "Sentiment": sentiment,
                "Memory_Size": len(engine.memory.short_term),
                "LT_Memory_Size": len(engine.memory.long_term),
                "LSTM_Status": "Simüle (PyTorch)" ,
                "Transformer_Status": "Simüle (Transformer)",
            }

            cached_data["portfolio"] = {
                "Kelly_F": kelly_f,
                "Risk_Parity_Weight": safe_v(1 / (volatility_annual + 0.01)),
                "Optimal_Size": safe_v(kelly_f * 0.5),
                "Max_Leverage": 2.0,
                "Efficient_Frontier_Sharpe": sharpe,
            }

            cached_data["macro"] = {
                "CPI": 310.5,
                "Interest_Rate": 5.25,
                "M2": 21200.0,
                "Sentiment_Score": sentiment,
            }

            cached_data["news"] = news if isinstance(news, list) else []
            cached_data["robot"] = {
                "action": signal,
                "tp": safe_v(tp),
                "sl": safe_v(sl),
                "prob_win": safe_v(win_rate),
                "prob_bull": safe_v(bull_prob),
                "prob_bear": safe_v(bear_prob)
            }

            cached_data["last_update"] = time.time()
            print(f">>> BASARILI. Ons: ${ons_price:.2f} | Gram: TRY{gram_price:.2f} | Sinyal: {signal}", flush=True)

        except Exception as e:
            print(f"!!! Hata: {e}", flush=True)
            import traceback
            traceback.print_exc()

        time.sleep(5)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def get_data():
    return jsonify(cached_data)


@app.route('/api/metrics')
def get_metrics():
    return jsonify({"metrics": cached_data["metrics"],
                    "risk": cached_data["risk"],
                    "ai": cached_data["ai"]})


if __name__ == "__main__":
    print("=== ALTIN ANALİZ TERMİNALİ v3.0 ===", flush=True)
    print("Adres: http://127.0.0.1:5000", flush=True)

    thread = threading.Thread(target=update_data_loop, daemon=True)
    thread.start()

    app.run(host='0.0.0.0', port=5000, debug=False)
