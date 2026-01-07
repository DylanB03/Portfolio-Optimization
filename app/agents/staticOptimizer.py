import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt import risk_models, expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
plt.style.use('fivethirtyeight')

# TICKERS
assets = ['META', 'AMZN', 'AAPL', 'NFLX', 'GOOG']

# weight assignment @ 20% each
weights = np.array([0.2, 0.2, 0.2, 0.2, 0.2])

#start date, end date
stockStartDate = '2013-01-01'
today = datetime.today().strftime('%Y-%m-%d')
print(today)

#dataframe for stock prices, get the last traded prices
df = pd.DataFrame()

for stock in assets:
    df[stock] = yf.download(stock, start = stockStartDate, end = today, progress = False)['Close']
    
#print(df)

# plot histories

title = 'Portfolio Close Price History'

for day in df.columns.values:
    plt.plot(df[day], label = day)

plt.title(title)
plt.xlabel('Date')
plt.ylabel('Price USD')
plt.legend(df.columns.values, loc = 'upper left')
# plt.show()

# get daily returns, diff dod

returns = df.pct_change()
print(returns)

# covariance matrix, risk, shows variance and correlations, multiplying by # of trading days
# diagonal is variance, else is covariance (diff from expected returns)

annual_cov = returns.cov() * 252

print(annual_cov)

variance = np.dot(weights.T, np.dot(annual_cov, weights))
print(variance)

# find volatility

volatility = np.sqrt(variance)
print(volatility)

# annual return
annual_return = np.sum(returns.mean() * weights) * 252
print(annual_return)

#optimize

#expected returns
mew = expected_returns.mean_historical_return(df)
#sample covariance matrix of asset returns
s = risk_models.sample_cov(df)

# max sharpe ratio, describe excess return given excess volatility in subtracting a risk free rate from a return / std dev
ef = EfficientFrontier(mew, s)
weights = ef.max_sharpe()
cleaned_weights = ef.clean_weights()
print(cleaned_weights)
ef.portfolio_performance(verbose = True)

# discrete allocation of share per stock

latest_prices = get_latest_prices(df)
da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value= 15000)
allocation, leftover = da.lp_portfolio()

print(allocation)
print(leftover)