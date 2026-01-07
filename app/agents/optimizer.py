from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from app.settings import Settings
from app.agents.geminiClient import GeminiClient
import logging
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import json
from uuid import uuid4
from app.models import ChatRequest, ChatResponse, GenerateRequest
import asyncio
from app.mcp.client.mcpExecutor import mcpExecutor

class OptimizerState(TypedDict):
    ticker: set
    startDate: str
    errors: set
    executionlog: set

class Optimizer:
    
    def __init__(self):
        
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        
        self.logger = logging.getLogger(__name__)
        
        self.llm = GeminiClient()
        
        self.executor = mcpExecutor(self.llm)
        
        self.setupGraph()
        
    def setupGraph(self):
        
        graph = StateGraph(OptimizerState)
        
        graph.add_node("initialize",self.initialize)
        graph.add_node("history",self.history)
        graph.add_node("plot", self.plot)
        graph.add_node("variables", self.variables)
        graph.add_node("optimize", self.optimize)
        graph.add_node("finalize", self.finalize)
        graph.add_node("error", self.error)
        
        graph.set_entry_point("initialize")
        graph.add_edge("intialize", "history")
        graph.add_edge("history", "plot")
        graph.add_edge("plot", "variables")
        graph.add_edge("variables", "optimize")
        graph.add_conditional_edges(
            "optimize",
            self.determineEnd,
            {
                "finalize":"finalize",
                "error": "error"
            }
        )
        graph.add_edge("finalize", END)
        graph.add_edge("error", END)
        
    async def initialize(self, state: OptimizerState):
        
        try:
            
            # check status of the executor (checks each MCP server)
            status = await self.executor.ping()
            
            self.logger.info(f"Received status from MCP Executor: {status}")
            
            #retrieve start date
            with open("app/prompts/optimizer_startDate.txt", "r") as file:
                prompt = file.read()
            
            date = await self.llm.generate_completion(
                request = GenerateRequest(prompt = prompt)
            )
            
            state["startDate"] = date.response
            
            self.logger.info(f"Selected start date for the optimization with at least 1 year of fiscal data available: {state['startDate']}")
            
            
            
            
        except Exception as e:
            state["executionlog"].append(f"Error encountered during initialization: {e}")
        
        return state
    
    async def history(self, state: OptimizerState):
        return state
    
    async def plot(self, state: OptimizerState):
        
        return state
    
    async def variables(self, state: OptimizerState):
        return state
    
    async def optimize(self, state: OptimizerState):
        return state
    
    async def finalize(self, state: OptimizerState):
        return state
    
    async def error(self, state: OptimizerState):
        return state 