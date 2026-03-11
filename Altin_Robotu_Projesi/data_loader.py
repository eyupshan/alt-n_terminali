import yfinance as yf
import pandas as pd
import numpy as np
import os

def _strip_tz(idx):
    """Zaman dilimi bilgisini güvenli şekilde kaldır."""
    idx = pd.to_datetime(idx)
    if idx.tz is not None:
        return idx.tz_localize(None)
    return idx

class GoldDataLoader:
    def __init__(self, fred_api_key=None):
        try:
            from fredapi import Fred
            self.fred = Fred(api_key=fred_api_key) if fred_api_key else None
        except ImportError:
            print("Uyarı: 'fredapi' kütüphanesi bulunamadı, makro veriler kapalı.")
            self.fred = None

    def _fetch_single(self, symbol: str, period: str, interval: str) -> pd.Series:
        """Tek bir sembol için Close serisi döndürür; boşsa None."""
        try:
            import requests
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Connection": "keep-alive"
            })
            
            hist = yf.download(symbol, period=period, interval=interval, session=session, progress=False, timeout=15)
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)
                
            if hist.empty or "Close" not in hist.columns:
                return None
            s = hist["Close"].copy()
            s.index = _strip_tz(s.index)
            s.name = symbol
            return s
        except Exception as ex:
            print(f"  [{symbol}] hata: {ex}")
            return None

    def fetch_gold_data(self, period="1y", interval="1d"):
        """
        Altın spot ve USD/TRY verisini yfinance'dan çeker.
        Gram Altın (TRY) = (XAU/USD / 31.1035) * USD/TRY
        """
        print("Piyasa verisi çekiliyor (yfinance çoklu sembol)...")

        gold_series = None
        gold_is_etf = False
        for sym in ["GC=F", "XAUUSD=X", "GLD"]:
            s = self._fetch_single(sym, period, interval)
            if s is not None and len(s) >= 1:
                gold_series = s
                gold_is_etf = (sym == "GLD")
                print(f"  [OK] Altın verisi: {sym} ({len(s)} veri)")
                break

        try_series = None
        for sym in ["USDTRY=X", "TRY=X"]:
            s = self._fetch_single(sym, period, interval)
            if s is not None and len(s) >= 1:
                try_series = s
                print(f"  [OK] USD/TRY verisi: {sym} ({len(s)} veri)")
                break

        if gold_series is None or try_series is None:
            raise ValueError(
                f"Veri çekilemedi: gold={'OK' if gold_series is not None else 'YOK'}, "
                f"try={'OK' if try_series is not None else 'YOK'}"
            )

        df = pd.DataFrame({"Gold_USD": gold_series, "USD_TRY": try_series})
        df = df.dropna(how="any")

        if len(df) < 1:
            idx_union = gold_series.index.union(try_series.index)
            gold_r = gold_series.reindex(idx_union).ffill()
            try_r = try_series.reindex(idx_union).ffill()
            df = pd.DataFrame({"Gold_USD": gold_r, "USD_TRY": try_r}).dropna()

        if len(df) < 1:
            raise ValueError(f"Birleştirilmiş veri yetersiz: {len(df)} satır")

        if gold_is_etf:
            df["Gold_USD"] = df["Gold_USD"] * 1

        df["Gram_Gold"] = (df["Gold_USD"] / 31.1035) * df["USD_TRY"]

        try:
            import requests
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Connection": "keep-alive"
            })
            vol_hist = yf.download("GC=F", period=period, interval=interval, session=session, progress=False)
            if isinstance(vol_hist.columns, pd.MultiIndex):
                vol_hist.columns = vol_hist.columns.get_level_values(0)
            if not vol_hist.empty and "Volume" in vol_hist.columns:
                vol = vol_hist["Volume"].copy()
                vol.index = _strip_tz(vol.index)
                df["Volume"] = vol.reindex(df.index).ffill().fillna(10000)
            else:
                df["Volume"] = 10000
        except Exception:
            df["Volume"] = 10000

        print(
            f"[OK] Veri hazır: {len(df)} periyot | "
            f"Son Ons: ${df['Gold_USD'].iloc[-1]:.2f} | "
            f"Son Gram: TL{df['Gram_Gold'].iloc[-1]:.2f}"
        )
        return df

    def fetch_news(self, query="gold price"):
        headlines = [
            "🚨 Altın fiyatları, yatırımcıların ABD enflasyon verilerine odaklanmasıyla yatay seyrediyor.",
            "🌍 Merkez bankaları, artan jeopolitik riskler nedeniyle altın rezervlerini hızla güçlendiriyor.",
            "📉 ABD Merkez Bankası'nın (Fed) olası faiz indirimi sinyalleri altına olan talebi canlandırdı.",
            "💵 Küresel piyasalarda güçlenen Dolar endeksi, gram altın ve spot ons fiyatları üzerinde kısa vadeli baskı yaratıyor.",
            "🔥 Asya piyasalarındaki rekor seviyedeki fiziksel altın talebi, fiyatlardaki olası büyük düşüşleri sınırlandırıyor.",
        ]
        return headlines

    def fetch_macro_indicators(self):
        if not self.fred:
            return pd.DataFrame(
                {
                    "CPI": [250, 251, 252],
                    "Interest_Rate": [5.25, 5.25, 5.5],
                    "M2_Money_Supply": [21000, 21100, 21200],
                }
            )
        indicators = {"CPI": "CPIAUCSLD", "Interest_Rate": "FEDFUNDS", "M2_Money_Supply": "M2SL", "GDP": "GDP", "Unemployment": "UNRATE"}
        macro_df = pd.DataFrame()
        for name, series_id in indicators.items():
            try: macro_df[name] = self.fred.get_series(series_id)
            except Exception: continue
        return macro_df

    def _synthetic_fallback(self):
        print("  [!] Sentetik (simüle) veri kullanılıyor...")
        dates = pd.date_range(end=pd.Timestamp.now().normalize(), periods=250, freq="B")
        np.random.seed(int(pd.Timestamp.now().timestamp()) % 10000)

        base_gold_usd = 2900.0   
        base_usdtry = 38.5       

        dt = 1 / 252
        gold_vol = 0.185 * np.sqrt(dt)
        try_vol = 0.20 * np.sqrt(dt)

        gold_rets = np.cumsum(np.random.normal(0.0003, gold_vol, 250))
        try_rets = np.cumsum(np.random.normal(0.0008, try_vol, 250))

        gold_usd = base_gold_usd * np.exp(gold_rets)
        usdtry = base_usdtry * np.exp(try_rets)

        df = pd.DataFrame(index=dates)
        df["Gold_USD"] = gold_usd
        df["USD_TRY"] = usdtry
        df["Gram_Gold"] = (df["Gold_USD"] / 31.1035) * df["USD_TRY"]
        df["Volume"] = np.random.randint(5000, 20000, size=250)
        return df

_orig_fetch = GoldDataLoader.fetch_gold_data

def _safe_fetch(self, period="1y", interval="1d"):
    try:
        return _orig_fetch(self, period=period, interval=interval)
    except Exception as e:
        print(f"Uyarı: yfinance tamamen başarısız ({e}). Sentetik veriye geçiliyor...")
        return self._synthetic_fallback()

GoldDataLoader.fetch_gold_data = _safe_fetch

if __name__ == "__main__":
    loader = GoldDataLoader()
    df = loader.fetch_gold_data(period="1y", interval="1d")
    print(df.tail())
    print(f"Son Ons: ${df['Gold_USD'].iloc[-1]:.2f} | Son Gram: TL{df['Gram_Gold'].iloc[-1]:.2f}")









