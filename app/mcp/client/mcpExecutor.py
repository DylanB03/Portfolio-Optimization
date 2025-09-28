from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from app.settings import Settings
from app.agents.geminiClient import GeminiClient
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import json
from uuid import uuid4
from app.models import ChatRequest, ChatResponse
import asyncio

class executionState(TypedDict):
    servers: list
    errors: list
    execution_log: list
    messages: list
    
class mcpExecutor():
    '''
    What: Agent for MCP standardized tool calling performed by LLM
    How: Workflow described with nodes
    '''
    def __init__(self,llm_client: GeminiClient):
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        self.logger = logging.getLogger(__name__)
        self.llm = llm_client
        self.httpx_client = httpx.AsyncClient()
        
        self.setup_graph()
        
    def setup_graph(self):
        
        graph = StateGraph(executionState)
        
        graph.add_node("initialize",self.initialize)
        graph.add_node("getArguments",self.getArguments)
        graph.add_node("executeTool",self.executeTool)
        graph.add_node("validation",self.validation)
        graph.add_node("finalization",self.finalization)
        graph.add_node("handleErrors",self.handleErrors)
        
        graph.set_entry_point('initialize')
        graph.add_edge('initialize','getArguments')
        graph.add_edge('getArguments','executeTool')
        graph.add_edge('executeTool','validation')
        
        graph.add_conditional_edges(
            "validation",
            self.determineEnd,
            {'finalization':'finalization','handleErrors':'handleErrors','getArguments':'getArguments'}
        )
        
        graph.add_edge('finalization',END)
        graph.add_edge('handleErrors',END)
        
        self.workflow = graph.compile()
        
    async def initialize(self,state: executionState) -> executionState:
        
        self.logger.info(f'Commencing MCP Initialization')
        
        self.mcp_headers = {server: {
            "Content-Type": "application/json",
            "Accept" : "application/json, text/event-stream",
            "MCP-Protocol-Version" : "2025-06-18"
            }
            for server in state["servers"]     
        }
        #follow MCP lifecycle, ping, initialize handshake
        for server in state["servers"]:
            ping_status = await self.ping(server)
            await self.handshake(server)
            self.logger.info(f'confirmed ping status - {ping_status} and initialized server: {server}')
        
        #now get the tools
        self.tools = await self.list_tools(state['servers'])
        self.logger.info(f'Verified the following tools: {self.tools}')
        
    async def getArguments(self,state: executionState) -> executionState:
        
        with open('app/prompts/mcpExecutor_getArguments.txt','r') as file:
            prompt = file.read()
            
        response = await self.llm.chat_completion(
            ChatRequest(
                model = Settings.GEMINI_MODEL,
                system_prompt=prompt,
                messages = state['messages'],
                tools = self.tools
            )
        )
        
        self.logger.info(f'Received the following arguments for a tool call: {response.response}')
        
        state["messages"].append({
            'role' : 'model',
            'parts' : [
                {'text' : response.response}
            ]
        })
        
    async def executeTool(self,state: executionState) -> executionState:
        
        
        
        self.logger.info('Commencing Tool Execution')
        
    async def validation(self,state: executionState) -> executionState:
        
        self.logger.info("Commencing Tool Output Validation")
        
    async def finalization(self, state: executionState) -> executionState:
        
        self.logger.info("Finalizing Request")
        
    async def handleErrors(self, state: executionState) -> executionState:
        
        self.logger.info("Finalizing Request, Errors Encountered")
        
    async def determineEnd(self, state: executionState) -> str:
        
        if state["problemStatus"]:
            if len(state["errors"]>0):
                return 'handleErrors'
            return 'finalization'
        return 'getArguments'
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min = 4, max=10),
        retry= retry_if_exception_type((httpx.TimeoutException,httpx.ConnectError))
    )   
    async def make_request(self, method: str, args: dict, url: str):
        try:
            self.logger.info(f"Attempting to make request to url: {url}")
            response =  await self.httpx_client.post(
                json={
                "jsonrpc": "2.0",
                "id": str(uuid4()),
                "method": method,
                "params": args
                },
                headers= self.mcp_headers,
                url=url
            )
            response.raise_for_status()

            response = json.loads(response.content.decode("utf-8"))
            
            return response.get("result",{}).get("content",[])[0].get("text")
        
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Failed with HTTP Status Error: {e}")
        
        except httpx.RequestError as e:
            self.logger.error(f"Failed with an HTTP Reqeust Error: {e}")  
                    
        except httpx.TimeoutException as e:
            self.logger.error(f"Failed with an HTTP Timeout Error: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed HTTP request with error: {e}")
            
    async def list_tools(self, servers):
        try:
            tools = []
            for server in servers:
                tool = await self.make_request(
                    method = "tools/list",
                    args = {},
                    url = server
                )
                tools.extend(tool)
            return tools
        except Exception as e:
            self.logger.error(f"Failed to list tools: {e}")
            
    async def tool_call(self, tool: str, args: dict):
        def convert_value(val):
            if isinstance(val, str):
                if val.lower() == "true":
                    return True
                if val.lower() == "false":
                    return False

                try:
                    if "." in val: 
                        return float(val)
                    return int(val)
                except ValueError:
                    return val 

            elif isinstance(val, list):
                return [convert_value(v) for v in val]

            elif isinstance(val, dict):
                return {k: convert_value(v) for k, v in val.items()}
        
        try:
            #validate typing incase of string formatting
            args = {k : convert_value(v) for k,v in args.items()}
            
            #find the url that it relates to

            url = None
            for k,v in self.tools:
                if tool in json.dumps(v):
                    url = k
            if not url:
                return {}
            
            return await self.make_request(
                    method = "tools/call",
                    args = {
                        "name" : tool,
                        "arguments" : args
                    },
                    url = url
                )
        
        except Exception as e:
            self.logger.error(f"Failed to call tool: {e}")
            
    async def ping(self,server):
        try:
            result = await self.httpx_client.post(
                url = server,
                headers = self.mcp_headers,
                json = {
                    "jsonrpc" : "2.0",
                    "id" : uuid4(),
                    "method" : "ping"
                }
            )
            
            return result.text
        
        except Exception as e:
            self.logger.error(f"Failed to ping server {server}: {e}")
    
    async def handshake(self,server):
        try:
            result = await self.httpx_client.post(
                url = server,
                headers = self.mcp_headers[server],
                json = {
                    "jsonrpc": "2.0",
                    "id" : 1,
                    "method" : "initialize",
                    "params" : {
                        "protocolVersion" : "2025-06-18",
                        "capabilities" : {}
                    },
                    "clientInfo" : {
                        "name" : "PortfolioOptimizerClient",
                        "version" : "1.0.0"
                        }   
                }
            )
            
            if 'Mcp-Session-Id' in result.headers:
                self.mcp_headers[server]['Mcp-Session-Id'] = result.headers['Mcp-Session-Id']
            
            await self.httpx_client.post(
                url = server,
                headers = self.mcp_headers[server],
                json = {
                    "jsonrpc" : "2.0",
                    "method" : "notifications/initialized"
                }
            )
        
        except Exception as e:
            self.logger.info(f"Failed performing initialization handshake on server {server} : {e}")
                
    def visualize_graph(self):
        try:
            return self.workflow.get_graph().draw_ascii()
        except Exception as e:
            self.logger.info(f'Failed drawing the graph: {e}')
            
    async def run(self,state: executionState):
        self.logger.info(f'Commencing a workflow execution')
        
        await self.workflow.ainvoke(state)
        
    

async def main():
    mcp = mcpExecutor(GeminiClient())
    print(mcp.visualize_graph())
    
    # state = executionState(
    #     servers=[], errors = [], execution_log=[], messages = []
    # )
    
    # await mcp.run(state)
    
if __name__ == '__main__':
    asyncio.run(main())