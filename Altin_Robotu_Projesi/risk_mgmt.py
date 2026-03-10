import pandas as pd
import numpy as np
from quant_math import QuantMath

class RiskParity:
    """
    Allocates capital based on inverse volatility (Risk Parity).
    """
    @staticmethod
    def calculate_weights(volatilities):
        inv_vol = 1.0 / np.array(volatilities)
        return inv_vol / np.sum(inv_vol)

class RiskManagement:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

    def calculate_performance_metrics(self, returns):
        if len(returns) < 2: return {}
        sharpe = np.sqrt(252) * returns.mean() / returns.std()
        downside_returns = returns[returns < 0]
        sortino = np.sqrt(252) * returns.mean() / downside_returns.std() if len(downside_returns) > 0 else 0
        cum_returns = (1 + returns).cumprod()
        rolling_max = cum_returns.cummax()
        drawdown = (cum_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        return {
            "Sharpe": round(sharpe, 2),
            "Sortino": round(sortino, 2),
            "Max_Drawdown": round(max_drawdown, 4)
        }

    def monte_carlo_stress_test(self, current_price, days=30, iterations=1000):
        """
        Runs Monte Carlo to estimate 95% worst-case drawdown.
        """
        returns = np.random.normal(0.0001, 0.02, (days, iterations))
        price_paths = current_price * (1 + returns).cumprod(axis=0)
        final_prices = price_paths[-1]
        var_95 = np.percentile(final_prices, 5)
        return var_95

    def position_sizing(self, win_prob, win_loss_ratio, volatility_score):
        kelly_f = QuantMath.kelly_criterion(win_prob, win_loss_ratio)
        vol_adj = 1.0 / (1.0 + volatility_score)
        return kelly_f * vol_adj

if __name__ == "__main__":
    rm = RiskManagement()
    dummy_returns = pd.Series(np.random.normal(0.001, 0.02, 100))
    print(rm.calculate_performance_metrics(dummy_returns))
