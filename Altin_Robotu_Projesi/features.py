import pandas as pd
import numpy as np
from scipy import stats

class GoldFeatures:

    @staticmethod
    def add_technical_indicators(df):
        """RSI, MACD, Bollinger Bands, ATR, Williams %R, CCI, MFI, Stochastic"""
        close = df['Gram_Gold']

        # RSI (Wilder's Smoothing)
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        exp12 = close.ewm(span=12, adjust=False).mean()
        exp26 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        # Bollinger Bands
        df['BB_Mid'] = close.rolling(20, min_periods=1).mean()
        df['BB_Std'] = close.rolling(20, min_periods=1).std(ddof=0)
        df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
        df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
        df['BB_Pct'] = (close - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower']).replace(0, np.nan)

        # ATR
        df['ATR'] = close.diff().abs().rolling(14, min_periods=1).mean()

        # Williams %R
        highest = close.rolling(14, min_periods=1).max()
        lowest = close.rolling(14, min_periods=1).min()
        df['Williams_R'] = -100 * (highest - close) / (highest - lowest).replace(0, np.nan)

        # CCI
        typical = close
        mad = typical.rolling(20, min_periods=1).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        df['CCI'] = (typical - typical.rolling(20, min_periods=1).mean()) / (0.015 * mad.replace(0, np.nan))

        # Stochastic
        df['Stoch_K'] = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
        df['Stoch_D'] = df['Stoch_K'].rolling(3, min_periods=1).mean()

        # Moving Averages (min_periods=1 hayat kurtarır)
        df['SMA_20'] = close.rolling(20, min_periods=1).mean()
        df['SMA_50'] = close.rolling(50, min_periods=1).mean()
        df['SMA_200'] = close.rolling(200, min_periods=1).mean()
        df['EMA_12'] = close.ewm(span=12, adjust=False).mean()
        df['EMA_26'] = close.ewm(span=26, adjust=False).mean()

        # OBV
        df['Price_Change'] = close.diff()
        df['OBV'] = (np.sign(df['Price_Change']) * df['Volume']).cumsum()

        # Tüm bozuk/eksik hesaplamaları sıfırla doldur (Çöküşü engeller)
        return df.fillna(0)

    @staticmethod
    def add_advanced_features(df):
        """Z-Score, Log Returns, Volatility, Hurst, Momentum, Mean Reversion"""
        close = df['Gram_Gold']

        df['Log_Return'] = np.log(close / close.shift(1).replace(0, np.nan))
        df['Pct_Return'] = close.pct_change()

        df['Volatility'] = df['Log_Return'].rolling(21, min_periods=1).std() * np.sqrt(252)
        df['Volatility_Short'] = df['Log_Return'].rolling(5, min_periods=1).std() * np.sqrt(252)

        lambda_decay = 0.94
        df['GARCH_Vol'] = df['Log_Return'].ewm(alpha=1-lambda_decay).std() * np.sqrt(252)

        roll_mean = close.rolling(20, min_periods=1).mean()
        roll_std = close.rolling(20, min_periods=1).std()
        df['Z_Score'] = (close - roll_mean) / roll_std.replace(0, np.nan)

        df['Momentum_5'] = close.pct_change(5)
        df['Momentum_20'] = close.pct_change(20)
        df['Momentum_60'] = close.pct_change(60)

        # 252 günlük pozisyon (Eksik günleri tolere eder)
        roll_min = close.rolling(252, min_periods=1).min()
        roll_max = close.rolling(252, min_periods=1).max()
        df['Price_Pos_52wk'] = (close - roll_min) / (roll_max - roll_min).replace(0, np.nan)

        def get_hurst_exponent(series):
            try:
                if len(series) < 10 or np.all(series == series[0]):
                    return 0.5
                lags = range(2, min(20, len(series)//3 + 1))
                tau = []
                for lag in lags:
                    t = np.sqrt(np.std(np.subtract(series[lag:], series[:-lag])))
                    tau.append(max(t, 1e-8))
                poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
                return float(np.clip(poly[0] * 2.0, 0, 1))
            except:
                return 0.5

        df['Hurst'] = close.rolling(min(100, len(df)), min_periods=10).apply(
            get_hurst_exponent, raw=True).ffill().fillna(0.5)

        try:
            lag_price = close.shift(1).dropna()
            delta_price = close.diff().dropna()
            common_idx = lag_price.index.intersection(delta_price.index)
            if len(common_idx) > 10:
                slope, _, _, _, _ = stats.linregress(lag_price.loc[common_idx], delta_price.loc[common_idx])
                half_life = -np.log(2) / slope if slope < 0 else np.nan
                df['Half_Life'] = round(float(half_life), 1) if not np.isnan(half_life) else 0
            else:
                df['Half_Life'] = 0
        except:
            df['Half_Life'] = 0

        df['Rolling_Sharpe'] = (df['Log_Return'].rolling(21, min_periods=1).mean() * 252) / \
            (df['Log_Return'].rolling(21, min_periods=1).std() * np.sqrt(252)).replace(0, np.nan)

        return df.fillna(0)

    @staticmethod
    def add_fibonacci_levels(df):
        max_val = df['Gram_Gold'].max()
        min_val = df['Gram_Gold'].min()
        diff = max_val - min_val
        df['Fib_0'] = min_val
        df['Fib_0236'] = max_val - 0.236 * diff
        df['Fib_0382'] = max_val - 0.382 * diff
        df['Fib_0500'] = max_val - 0.5 * diff
        df['Fib_0618'] = max_val - 0.618 * diff
        df['Fib_0786'] = max_val - 0.786 * diff
        df['Fib_1000'] = max_val
        return df.fillna(0)

    @staticmethod
    def add_volatility_regime(df, window=21):
        df['Vol_Mean'] = df['Volatility'].rolling(window * 5, min_periods=1).mean()
        df['Vol_Regime'] = np.where(df['Volatility'] > df['Vol_Mean'], 'YÜKSEK', 'DÜŞÜK')
        return df.fillna(0)

    @staticmethod
    def add_market_regime(df, window=50):
        ma = df['Gram_Gold'].rolling(window, min_periods=1).mean()
        df['Regime'] = 'YATAY'
        df.loc[(df['Gram_Gold'] > ma) & (df['RSI'] > 55), 'Regime'] = 'BOĞA'
        df.loc[(df['Gram_Gold'] < ma) & (df['RSI'] < 45), 'Regime'] = 'AYI'
        return df.fillna(0)

    @staticmethod
    def add_strategy_signals(df):
        df['Signal_Momentum'] = np.where(df['Momentum_20'] > 0.02, 'AL',
                                np.where(df['Momentum_20'] < -0.02, 'SAT', 'BEKLE'))

        df['Signal_MeanRev'] = np.where(df['Z_Score'] < -2.0, 'AL',
                               np.where(df['Z_Score'] > 2.0, 'SAT', 'BEKLE'))

        df['Golden_Cross'] = (df['SMA_20'] > df['SMA_50']) & (df['SMA_20'].shift(1) <= df['SMA_50'].shift(1))
        df['Death_Cross'] = (df['SMA_20'] < df['SMA_50']) & (df['SMA_20'].shift(1) >= df['SMA_50'].shift(1))
        df['Signal_Trend'] = np.where(df['SMA_20'] > df['SMA_50'], 'AL', 'SAT')

        df['Signal_Combined'] = 'BEKLE'
        df.loc[(df['RSI'] < 40) & (df['MACD_Hist'] > 0), 'Signal_Combined'] = 'AL'
        df.loc[(df['RSI'] > 60) & (df['MACD_Hist'] < 0), 'Signal_Combined'] = 'SAT'

        return df.fillna(0)

    @staticmethod
    def add_econometric_features(df):
        close = df['Gram_Gold']
        returns = df['Log_Return']

        try:
            df['Autocorr_Lag1'] = returns.rolling(30, min_periods=1).corr(returns.shift(1))
        except:
            df['Autocorr_Lag1'] = 0

        df['Rolling_Skew'] = returns.rolling(30, min_periods=1).skew()
        df['Rolling_Kurt'] = returns.rolling(30, min_periods=1).kurt()
        df['Price_Accel'] = close.diff().diff()

        return df.fillna(0)
