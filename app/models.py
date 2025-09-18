from pydantic import BaseModel

class GenerateRequest(BaseModel):
    model : str = "gemini-2.5-flash"
    prompt : str

class GenerateResponse(BaseModel):
    response : str

class ChatRequest(BaseModel):
    model : str = "gemini-2.5-flash"
    system_prompt : str = "Respond concisely to the user query",
    tools = list
    messages: list

class ChatResponse(BaseModel):
    response : str
