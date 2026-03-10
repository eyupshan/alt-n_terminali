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

        # Bollinger Bands (Population Standard Deviation, ddof=0)
        df['BB_Mid'] = close.rolling(20).mean()
        df['BB_Std'] = close.rolling(20).std(ddof=0)
        df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
        df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
        df['BB_Pct'] = (close - df['BB_Lower']) / (df['BB_Upper'] - df['BB_Lower']).replace(0, np.nan)

        # ATR
        df['ATR'] = close.diff().abs().rolling(14).mean()

        # Williams %R
        highest = close.rolling(14).max()
        lowest = close.rolling(14).min()
        df['Williams_R'] = -100 * (highest - close) / (highest - lowest).replace(0, np.nan)

        # CCI (Mean Absolute Deviation formula)
        typical = close  # Orijinalde (H+L+C)/3 olur, min/max yoksa kapanış fiyatı referans alınır.
        mad = typical.rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        df['CCI'] = (typical - typical.rolling(20).mean()) / (0.015 * mad.replace(0, np.nan))

        # Stochastic (simplified)
        df['Stoch_K'] = 100 * (close - lowest) / (highest - lowest).replace(0, np.nan)
        df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

        # Moving Averages
        df['SMA_20'] = close.rolling(20).mean()
        df['SMA_50'] = close.rolling(50).mean()
        df['SMA_200'] = close.rolling(200).mean()
        df['EMA_12'] = close.ewm(span=12, adjust=False).mean()
        df['EMA_26'] = close.ewm(span=26, adjust=False).mean()

        # OBV (Volume-based)
        df['Price_Change'] = close.diff()
        df['OBV'] = (np.sign(df['Price_Change']) * df['Volume']).cumsum()

        return df

    @staticmethod
    def add_advanced_features(df):
        """Z-Score, Log Returns, Volatility, Hurst, Momentum, Mean Reversion"""
        close = df['Gram_Gold']

        # Returns
        df['Log_Return'] = np.log(close / close.shift(1))
        df['Pct_Return'] = close.pct_change()

        # Volatility (realized)
        df['Volatility'] = df['Log_Return'].rolling(21).std() * np.sqrt(252)
        df['Volatility_Short'] = df['Log_Return'].rolling(5).std() * np.sqrt(252)

        # GARCH-like conditional volatility (EWMA)
        lambda_decay = 0.94
        df['GARCH_Vol'] = df['Log_Return'].ewm(alpha=1-lambda_decay).std() * np.sqrt(252)

        # Z-Score (Mean Reversion)
        roll_mean = close.rolling(20).mean()
        roll_std = close.rolling(20).std()
        df['Z_Score'] = (close - roll_mean) / roll_std.replace(0, np.nan)

        # Momentum
        df['Momentum_5'] = close.pct_change(5)
        df['Momentum_20'] = close.pct_change(20)
        df['Momentum_60'] = close.pct_change(60)

        # Price position (in range)
        df['Price_Pos_52wk'] = (close - close.rolling(252).min()) / \
            (close.rolling(252).max() - close.rolling(252).min()).replace(0, np.nan)

        # Hurst Exponent (Approx)
        def get_hurst_exponent(series):
            try:
                if len(series) < 30 or np.all(series == series[0]):
                    return 0.5
                lags = range(2, min(20, len(series)//3))
                tau = []
                for lag in lags:
                    t = np.sqrt(np.std(np.subtract(series[lag:], series[:-lag])))
                    tau.append(max(t, 1e-8))
                poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
                return float(np.clip(poly[0] * 2.0, 0, 1))
            except:
                return 0.5

        df['Hurst'] = close.rolling(min(100, len(df))).apply(
            get_hurst_exponent, raw=True).ffill().fillna(0.5)

        # Half-Life of Mean Reversion (OLS)
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

        # Sharpe per period (rolling)
        df['Rolling_Sharpe'] = (df['Log_Return'].rolling(21).mean() * 252) / \
            (df['Log_Return'].rolling(21).std() * np.sqrt(252)).replace(0, np.nan)

        return df

    @staticmethod
    def add_fibonacci_levels(df):
        """Fibonacci retracement seviyeleri"""
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
        return df

    @staticmethod
    def add_volatility_regime(df, window=21):
        """Yüksek/Düşük volatilite rejimi"""
        df['Vol_Mean'] = df['Volatility'].rolling(window * 5).mean()
        df['Vol_Regime'] = np.where(df['Volatility'] > df['Vol_Mean'], 'YÜKSEK', 'DÜŞÜK')
        return df

    @staticmethod
    def add_market_regime(df, window=50):
        """Boğa/Ayı/Yatay piyasa rejimi"""
        ma = df['Gram_Gold'].rolling(window).mean()
        df['Regime'] = 'YATAY'
        df.loc[(df['Gram_Gold'] > ma) & (df['RSI'] > 55), 'Regime'] = 'BOĞA'
        df.loc[(df['Gram_Gold'] < ma) & (df['RSI'] < 45), 'Regime'] = 'AYI'
        return df

    @staticmethod
    def add_strategy_signals(df):
        """Strateji sinyalleri: Momentum, Mean Reversion, Trend"""
        close = df['Gram_Gold']

        # Momentum Stratejisi
        df['Signal_Momentum'] = np.where(df['Momentum_20'] > 0.02, 'AL',
                                np.where(df['Momentum_20'] < -0.02, 'SAT', 'BEKLE'))

        # Mean Reversion Stratejisi
        df['Signal_MeanRev'] = np.where(df['Z_Score'] < -2.0, 'AL',
                               np.where(df['Z_Score'] > 2.0, 'SAT', 'BEKLE'))

        # Trend Following (Golden/Death Cross)
        df['Golden_Cross'] = (df['SMA_20'] > df['SMA_50']) & (df['SMA_20'].shift(1) <= df['SMA_50'].shift(1))
        df['Death_Cross'] = (df['SMA_20'] < df['SMA_50']) & (df['SMA_20'].shift(1) >= df['SMA_50'].shift(1))
        df['Signal_Trend'] = np.where(df['SMA_20'] > df['SMA_50'], 'AL', 'SAT')

        # RSI + MACD Combined
        df['Signal_Combined'] = 'BEKLE'
        df.loc[(df['RSI'] < 40) & (df['MACD_Hist'] > 0), 'Signal_Combined'] = 'AL'
        df.loc[(df['RSI'] > 60) & (df['MACD_Hist'] < 0), 'Signal_Combined'] = 'SAT'

        return df

    @staticmethod
    def add_econometric_features(df):
        """ARIMA residuals, ADF test yaklaşımı, Autocorrelation"""
        close = df['Gram_Gold']
        returns = df['Log_Return']

        # Autocorrelation at lag 1
        try:
            df['Autocorr_Lag1'] = returns.rolling(30).corr(returns.shift(1))
        except:
            df['Autocorr_Lag1'] = 0

        # Skewness and Kurtosis
        df['Rolling_Skew'] = returns.rolling(30).skew()
        df['Rolling_Kurt'] = returns.rolling(30).kurt()

        # Price acceleration
        df['Price_Accel'] = close.diff().diff()

        return df


if __name__ == "__main__":
    from data_loader import GoldDataLoader
    loader = GoldDataLoader()
    df = loader.fetch_gold_data()
    features = GoldFeatures()
    df = features.add_technical_indicators(df)
    df = features.add_advanced_features(df)
    print(df[['Gram_Gold', 'RSI', 'MACD', 'Z_Score', 'Hurst', 'Volatility']].tail(5))
