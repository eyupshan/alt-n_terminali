import numpy as np
import pandas as pd
from scipy.stats import norm

class QuantMath:
    @staticmethod
    def geometric_brownian_motion(S0, mu, sigma, T, steps, N_paths):
        """
        Simulates price paths using Geometric Brownian Motion (GBM).
        dS = mu*S*dt + sigma*S*dW
        """
        dt = T / steps
        paths = np.zeros((steps + 1, N_paths))
        paths[0] = S0
        
        for i in range(1, steps + 1):
            W = np.random.standard_normal(N_paths)
            paths[i] = paths[i-1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * W)
            
        return paths

    @staticmethod
    def kelly_criterion(win_prob, win_loss_ratio):
        """
        Calculates optimal position size using Kelly Criterion.
        f* = (bp - q) / b
        """
        p = win_prob
        q = 1 - p
        b = win_loss_ratio
        if b == 0: return 0
        f_star = (b * p - q) / b
        return max(0, f_star) # No leverage or short for now

    @staticmethod
    def calculate_var(returns, confidence_level=0.95):
        """
        Value at Risk (Historical)
        """
        return np.percentile(returns, 100 * (1 - confidence_level))

    @staticmethod
    def calculate_cvar(returns, confidence_level=0.95):
        """
        Conditional Value at Risk (Expected Shortfall)
        """
        var = QuantMath.calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()

    @staticmethod
    def black_scholes(S, K, T, r, sigma, option_type="call"):
        """
        Standard Black-Scholes Option Pricing.
        """
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if option_type == "call":
            return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:
            return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    @staticmethod
    def get_hurst_exponent(series, window=100):
        """
        Calculates Hurst Exponent for trend strength estimation.
        H < 0.5: Mean Reverting
        H = 0.5: Random Walk
        H > 0.5: Trending
        """
        if len(series) < 10: return 0.5
        lags = range(2, 20)
        tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

if __name__ == "__main__":
    # Test GBM
    math = QuantMath()
    paths = math.geometric_brownian_motion(100, 0.05, 0.2, 1, 252, 10)
    print(f"GBM Final Mean: {paths[-1].mean()}")
    print(f"Kelly for 55% win and 2:1 ratio: {math.kelly_criterion(0.55, 2)}")
