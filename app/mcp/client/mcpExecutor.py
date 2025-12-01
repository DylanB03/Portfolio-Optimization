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
    tools: list
    errors: list
    execution_log: list
    messages: list
    arguments: dict
    context: list
    problemStatus: bool


class mcpExecutor:
    """
    Agent for MCP standardized tool calling using LangGraph
    """

    def __init__(self, llm_client: GeminiClient):

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        self.logger = logging.getLogger(__name__)
        self.llm = llm_client
        self.httpx_client = httpx.AsyncClient()
        self.mcp_headers = {}

        self.setup_graph()


    def setup_graph(self):

        graph = StateGraph(executionState)

        graph.add_node("initialize", self.initialize)
        graph.add_node("getArguments", self.getArguments)
        graph.add_node("executeTool", self.executeTool)
        graph.add_node("validation", self.validation)
        graph.add_node("finalization", self.finalization)
        graph.add_node("handleErrors", self.handleErrors)

        graph.set_entry_point("initialize")
        graph.add_edge("initialize", "getArguments")
        graph.add_edge("getArguments", "executeTool")
        graph.add_edge("executeTool", "validation")

        graph.add_conditional_edges(
            "validation",
            self.determineEnd,
            {
                "finalization": "finalization",
                "handleErrors": "handleErrors",
                "getArguments": "getArguments",
            },
        )

        graph.add_edge("finalization", END)
        graph.add_edge("handleErrors", END)

        self.workflow = graph.compile()


    async def initialize(self, state: executionState) -> executionState:

        self.logger.info(f"Commencing MCP Initialization")

        self.mcp_headers = {
            server: {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": "2025-06-18"
            } for server in state["servers"]
        }

        for server in state["servers"]:
            ping_status = await self.ping(server)
            await self.handshake(server)
            self.logger.info(f"Server {server} ping OK: {ping_status}")

        state["tools"] = await self.list_tools(state["servers"])
        self.logger.info(f"Verified tools: {state['tools']}")

        return state

    async def getArguments(self, state: executionState) -> executionState:

        try:
            self.logger.info("Generating arguments for tool call")

            with open("app/prompts/mcpExecutor_getArguments.txt", "r") as file:
                prompt = file.read()

            resp = await self.llm.chat_completion(
                ChatRequest(
                    model=Settings.GEMINI_MODEL,
                    system_prompt=prompt,
                    messages=state["messages"],
                    tools=state["tools"],
                )
            )

            state["arguments"] = resp.response
            state["messages"].append({"role": "model", "parts": [{"text": resp.response}]})

        except Exception as e:
            self.logger.error(f"Argument generation failed: {e}")
            state["errors"].append(str(e))

        return state

    async def executeTool(self, state: executionState) -> executionState:

        try:
            self.logger.info("Executing tool")

            if state["arguments"].get("completed"):
                self.logger.info("LLM says request is completed; skipping tool")
                return state

            tool = state["arguments"].get("tool")
            args = state["arguments"].get("args")

            if not tool or args is None:
                self.logger.error("Missing tool or args")
                state["errors"].append("Missing tool or args")
                return state

            response = await self.tool_call(tool, args, state["tools"])

            if isinstance(response, str) and "error" in response.lower():
                state["messages"].append({
                    "role": "user",
                    "parts": [{
                        "text": f"Tool error. Provide new arguments. RESPONSE: {response}"
                    }]
                })
            else:
                state["context"].append(response)
                state["messages"].append({
                    "role": "user",
                    "parts": [{
                        "text": f"New context received: {response}"
                    }]
                })

        except Exception as e:
            self.logger.error(f"Tool execution failure: {e}")
            state["errors"].append(str(e))

        return state

    async def validation(self, state: executionState) -> executionState:

        self.logger.info("Validating tool output")

        if len(state["errors"]) > 0:
            state["problemStatus"] = True
        else:
            state["problemStatus"] = True  # assume finished for now

        return state

    async def finalization(self, state: executionState) -> executionState:
        self.logger.info("Finalizing request")
        return state

    async def handleErrors(self, state: executionState) -> executionState:
        self.logger.info("Errors encountered, finalizing with errors")
        return state

    async def determineEnd(self, state: executionState) -> str:

        if state["problemStatus"]:
            if len(state["errors"]) > 0:
                return "handleErrors"
            return "finalization"
        return "getArguments"


    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    async def make_request(self, method: str, args: dict, url: str):
        try:
            self.logger.info(f"Request to {url} - {method}")

            response = await self.httpx_client.post(
                url=url,
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid4()),
                    "method": method,
                    "params": args,
                },
                headers=self.mcp_headers[url],
            )

            response.raise_for_status()

            data = response.json()
            if "result" in data:
                try:
                    return data["result"]["content"][0]["text"]
                except:
                    return json.dumps(data["result"])

        except Exception as e:
            self.logger.error(f"HTTP failure: {e}")
            return json.dumps({"error": str(e)})

    async def list_tools(self, servers):

        tools = []

        for server in servers:
            raw = await self.make_request("tools/list", {}, server)
            try:
                parsed = json.loads(raw)
                for t in parsed:
                    tools.append((server, t))
            except:
                pass

        return tools

    async def tool_call(self, tool: str, args: dict, tools: list):

        def convert_value(val):
            if isinstance(val, str):
                if val.lower() == "true": return True
                if val.lower() == "false": return False
                try:
                    if "." in val:
                        return float(val)
                    return int(val)
                except:
                    return val
            if isinstance(val, list):
                return [convert_value(v) for v in val]
            if isinstance(val, dict):
                return {k: convert_value(v) for k, v in val.items()}
            return val

        try:
            args = {k: convert_value(v) for k, v in args.items()}

            url = None
            for srv, tool_info in tools:
                if tool == tool_info.get("name"):
                    url = srv

            if not url:
                return json.dumps({"error": "Tool not found"})

            return await self.make_request(
                "tools/call",
                {"name": tool, "arguments": args},
                url=url,
            )

        except Exception as e:
            self.logger.error(f"Tool call failed: {e}")
            return json.dumps({"error": str(e)})


    async def ping(self, server):
        try:
            resp = await self.httpx_client.post(
                url=server,
                headers=self.mcp_headers[server],
                json={"jsonrpc": "2.0", "id": uuid4(), "method": "ping"},
            )
            return resp.text
        except Exception as e:
            return f"Ping failed: {e}"

    async def handshake(self, server):
        try:
            result = await self.httpx_client.post(
                url=server,
                headers=self.mcp_headers[server],
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {}
                    },
                    "clientInfo": {
                        "name": "PortfolioOptimizerClient",
                        "version": "1.0.0"
                    }
                }
            )

            if "Mcp-Session-Id" in result.headers:
                self.mcp_headers[server]["Mcp-Session-Id"] = result.headers["Mcp-Session-Id"]

            await self.httpx_client.post(
                url=server,
                headers=self.mcp_headers[server],
                json={
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
            )

        except Exception as e:
            self.logger.error(f"Handshake failed: {e}")

    # ---------------------------------------------------------------------
    # ENTRYPOINT
    # ---------------------------------------------------------------------
    async def run(self, state: executionState):
        self.logger.info("Starting workflow...")
        await self.workflow.ainvoke(state)

    def visualize_graph(self):
        try:
            return self.workflow.get_graph().draw_ascii()
        except Exception as e:
            return f"Cannot draw graph: {e}"



async def main():
    mcp = mcpExecutor(GeminiClient())
    print(mcp.visualize_graph())

    # Example state
    # state = executionState(
    #     servers=["http://localhost:5000"],
    #     tools=[],
    #     errors=[],
    #     execution_log=[],
    #     messages=[],
    #     arguments={},
    #     context=[],
    #     problemStatus=False
    # )
    #
    # await mcp.run(state)

if __name__ == "__main__":
    asyncio.run(main())
