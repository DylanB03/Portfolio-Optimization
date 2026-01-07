from mcp.server.fastmcp import FastMCP
from polygon.rest import RESTClient
from app.settings import Settings

class polygonMCP():
    
    def __init__(self, api_key: str):
        
        self.market_client = RESTClient(api_key=api_key)
        self.mcp = FastMCP(
            "A StockMarket MCP Server Integrating Polygon",
            host='0.0.0.0',
            port='8080',
            streamable_http_path='/mcp',
            debug=False
            )
        self.load_tools()
        
    def load_tools(self):
        
        @self.mcp.tool()
        async def get_last_trade(ticker):
            return self.market_client.get_last_trade()
        
        @self.mcp.tool()
        async def list_trades(ticker, timestamp):
            return self.market_client.list_trades(ticker,timestamp)
        
        @self.mcp.tool()
        async def get_last_quote(ticker):
            return self.market_client.get_last_quote(ticker)
        
        @self.mcp.tool()
        async def get_data(ticker, start, end):
            return self.market_client.get_aggs(
                ticker = ticker,
                multiplier = 1,
                timespan = "day",
                from_=start,
                to = end,
                adjusted = True
            )
        
        
    def run(self):
        print('running the server')
        self.mcp.run(transport='streamable-http')


if __name__ == '__main__':
    poly = polygonMCP(Settings.POLYGON_API_KEY)
    poly.run()
    