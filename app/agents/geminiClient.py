from app.settings import Settings
from google import genai
from google.genai import types
from app.models import GenerateRequest, GenerateResponse, ChatRequest, ChatResponse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

class GeminiClient:
    '''
    Class to be imported whenever an LLM call needs to be made
    Why: Simplifies API calls
    '''

    def __init__(self):
        
        self.logger = logging.getLogger(__name__)
        self.settings = Settings
        self.client = genai.Client(api_key=self.settings.GEMINI_API_KEY) 

    def generate_completion(self,request: GenerateRequest) -> GenerateResponse:
        self.logger.info(f"generating from a prompt {request.prompt}")
        response = self.client.models.generate_content(
            model=request.model,
            contents=request.prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
        )
        self.logger.info(f"received a response {response.text}")
        return GenerateResponse(response=response.text)
    
    def chat_completion(self,request: ChatRequest) -> ChatResponse:
        self.logger.info(f"sending a chat request {request.prompt}")

        #pull relevant data from graphdb
        response = self.client.models.generate_content(
            model=request.model,
            config = types.GenerateContentConfig(
                system_instruction=request.system_prompt,
                thinking_config=types.ThinkingConfig(thinking_budget=0)
            ),
            contents=request.prompt
        )
        self.logger.info(f"received a chat response {response.text}")
        return GenerateResponse(response=response.text)

def main():

    geminiInstance = GeminiClient()
    
    geminiInstance.generate_completion(GenerateRequest(prompt='What is the color of the sky and why'))
    
if __name__ == "__main__":
    main()
