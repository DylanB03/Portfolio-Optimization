# Markowitz Mean Variance Optimization

### Notes Reference

[
https://sites.math.washington.edu/~burke/crs/408/fin-proj/mark1.pdf 
]()

## Notes:

### Portfolio Return Rates

Return on asset (ratio):
![alt text](image.png)

Rate of return on asset: 
![alt text](image-1.png)

Selling assets you dont own = short selling (shorting).
Example: 
- Get a brokerage to sell some stock that they own, in X amount of stocks
- X stock is credited against your acount, denominated in X stocks, not dollars
- This is considered a negative asset
- You get the money from them selling it, and eventually the brokerage rebuys the stock and you hope it is cheaper than when you sold it

Situation:
- You have a portfolio with *n* assets, and an initial budget of *x0*, wanting to assign a budget to each individual assetg
- Representing budget assigned to asset *i* with *x0i* = *wix0* for i = 1,2...,n and *wi* is a weight for asset i
- Negative weights represent a shorted asset
- Budget preservation requires
![alt text](image-2.png)
and the sum of weights = 1
- The negative value of short weights is important, as getting the money gives you funds to purchase more assets
- *Ri* = return on asset *i*, sum of returns is
![alt text](image-3.png)
- Use the initial formula of rate of return on an asset to find the rate of return on the portfolio
![alt text](image-4.png)

### Markowitz Mean Variance Portfolio Theory
