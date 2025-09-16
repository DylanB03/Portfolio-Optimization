from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from app.settings import Settings
from app.agents.geminiClient import GeminiClient
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import json
from uuid import uuid4

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
        self.httpx_client = httpx.AsyncClient(
            headers = {
                "Content-Type": "application/json",
                "Accept" : "application/json, text/event-stream",
                "MCP-Protocol-Version" : "2025-06-18"
            }
        )
        
        self.setup_graph()
        
    def setup_graph(self):
        
        graph = StateGraph(executionState)
        
        graph.add_node("initialize",self.initialize)
        graph.add_node("getArgument",self.getArguments)
        graph.add_node("executeTool",self.executeTool)
        graph.add_node("validation",self.validation)
        graph.add_node("finalization",self.finalization)
        graph.add_node("handleErrors",self.handleErrors)
        
        graph.set_entry_point('initialization')
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
        
    async def getArguments(self,state: executionState) -> executionState:
        
    async def executeTool(self,state: executionState) -> executionState:
        
    async def validation(self,state: executionState) -> executionState:
        
    async def finalization(self, state: executionState) -> executionState:
        
    async def handleErrors(self, state: executionState) -> executionState:
        
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
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                },
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
            
        async def list_tools(self):
            try:
                
                return await self.make_request(
                        method = "tools/list",
                        args = {}
                    )
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
                return await self.make_request(
                        method = "tools/call",
                        args = {
                            "name" : tool,
                            "arguments" : args
                        }
                    )
            
            except Exception as e:
                self.logger.error(f"Failed to call tool: {e}")
                
    
            