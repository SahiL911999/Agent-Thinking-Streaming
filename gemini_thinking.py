import os
from typing import Any, List, Optional, Iterator
from dotenv import load_dotenv

# 1. Standard Imports
from google import genai
from google.genai import types

# UPDATED: We use SimpleChatModel instead of LLM
from langchain_core.language_models.chat_models import SimpleChatModel 
from langchain_core.messages import BaseMessage, AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk

# 2. LangGraph Imports
from langgraph.prebuilt import create_react_agent
from langgraph.config import get_stream_writer 

load_dotenv()

# --- PART 1: THE CUSTOM CHAT MODEL ---
# Inherit from SimpleChatModel (The "Round Peg")
class GeminiReasoningChat(SimpleChatModel):
    client: Any = None
    model_name: str = "gemini-2.5-flash"
    api_key: str = None
    thinking_budget: int = 1024 

    def __init__(self, thinking_budget: int = 1024, **kwargs):
        super().__init__(**kwargs)
        self.thinking_budget = thinking_budget
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key)

    @property
    def _llm_type(self) -> str:
        return "gemini-reasoning-chat"

    # Required: Helper to format messages into a prompt for Google
    def _format_prompt(self, messages: List[BaseMessage]) -> str:
        # Simple strategy: Combine all message contents
        # In a real app, you would format this properly with roles
        return "\n".join([m.content for m in messages])

    # Required: The main logic for non-streaming calls
    def _call(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs) -> str:
        prompt = self._format_prompt(messages)
        # We just reuse the stream logic to avoid duplicate code
        combined_text = ""
        for chunk in self._stream(messages, stop, **kwargs):
            combined_text += chunk.content
        return combined_text

    # THE MAIN LOGIC: Streaming
    def _stream(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs) -> Iterator[ChatGenerationChunk]:
        
        # 1. Convert Messages to Prompt
        prompt = self._format_prompt(messages)
        
        # 2. Get the Writer
        writer = None
        try:
            writer = get_stream_writer()
        except Exception:
            writer = None 

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=self.thinking_budget
            ),
            temperature=0
        )

        stream = self.client.models.generate_content_stream(
            model=self.model_name,
            contents=prompt,
            config=config
        )

        for chunk in stream:
            if not chunk.candidates or not chunk.candidates[0].content.parts:
                continue

            for part in chunk.candidates[0].content.parts:
                
                # A. If it's THINKING
                if part.thought:
                    if writer:
                        # Send text, not boolean
                        writer({"thought": part.text}) 
                
                # B. If it's ANSWER
                elif part.text:
                    # UPDATED: Yield an AIMessageChunk, not a GenerationChunk
                    yield ChatGenerationChunk(
                        message=AIMessageChunk(content=part.text)
                    )


# --- PART 2: THE SETUP ---
model = GeminiReasoningChat(thinking_budget=1024)

# create_react_agent now receives a valid Chat Model
agent = create_react_agent(model, tools=[])


# --- PART 3: THE CHAT LOOP ---
print("--- LANGCHAIN CUSTOM STREAMING (FINAL) ---")

while True:
    user_input = input("\n\033[94mYou: \033[0m") 
    if user_input.lower() in ["exit", "quit"]: break
    
    print("\n", end="") 

    try:
        # Stream with the correct mode
        for mode, chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            stream_mode=["messages", "custom"]
        ):
            
            # CASE 1: The Thinking (Gray)
            if mode == "custom":
                if "thought" in chunk:
                    print(f"\033[90m{chunk['thought']}\033[0m", end="", flush=True)

            # CASE 2: The Answer (Green)
            elif mode == "messages":
                msg, metadata = chunk
                # Now this check will pass correctly!
                if isinstance(msg, AIMessageChunk):
                    print(f"\033[92m{msg.content}\033[0m", end="", flush=True)
    
    except Exception as e:
        print(f"\n\033[91mError: {e}\033[0m")

    print("\033[0m\n")





# import os
# from typing import Any, List, Optional, Iterator
# from dotenv import load_dotenv

# # 1. Imports
# from google import genai
# from google.genai import types
# from langchain_core.language_models import LLM
# from langchain_core.outputs import GenerationChunk
# from langchain.agents import create_agent
# from langchain_core.tools import tool

# load_dotenv()

# # --- PART 1: THE CUSTOM BRAIN ---
# class GeminiReasoningLLM(LLM):
#     client: Any = None
#     model_name: str = "gemini-2.5-flash" # Updated to the latest thinking model
#     api_key: str = None
#     thinking_budget: int = 1024 

#     def __init__(self, thinking_budget: int = 1024, **kwargs):
#         super().__init__(**kwargs)
#         self.thinking_budget = thinking_budget
#         self.api_key = os.getenv("GOOGLE_API_KEY")
#         self.client = genai.Client(api_key=self.api_key)

#     @property
#     def _llm_type(self) -> str:
#         return "gemini-reasoning"

#     def _call(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> str:
#         combined_text = ""
#         for chunk in self._stream(prompt, stop, **kwargs):
#             combined_text += chunk.text
#         return combined_text

#     # --- PART 2: THE MODIFIED LOGIC ---
#     def _stream(self, prompt: str, stop: Optional[List[str]] = None, **kwargs) -> Iterator[GenerationChunk]:
        
#         # 1. Configure the "Thinking" capability
#         config = types.GenerateContentConfig(
#             thinking_config=types.ThinkingConfig(
#                 include_thoughts=True,
#                 thinking_budget=self.thinking_budget
#             ),
#             temperature=0
#         )

#         # 2. Call Google API
#         stream = self.client.models.generate_content_stream(
#             model=self.model_name,
#             contents=prompt,
#             config=config
#         )

#         # 3. Process the stream chunk-by-chunk
#         print("\033[90mThinking Process:\n", end="") # Header for thoughts
        
#         for chunk in stream:
#             if not chunk.candidates or not chunk.candidates[0].content.parts:
#                 continue

#             for part in chunk.candidates[0].content.parts:
                
#                 # A. If it's THINKING (Gray Text) -> PRINT THIS
#                 if part.thought:
#                     print(f"{part.text}", end="", flush=True) 
                
#                 # B. If it's ANSWER (Green Text) -> DO NOT PRINT, JUST YIELD
#                 elif part.text:
#                     # We removed the print statement here.
#                     # We silently hand the text to LangChain.
#                     yield GenerationChunk(text=part.text)
        
#         print("\033[0m") # Reset color after thinking is done



# # --- PART 3: THE SETUP ---

# # Initialize the custom model
# model = GeminiReasoningLLM(thinking_budget=1024)

# # Create the agent
# agent = create_agent(
#     model=model,
#     system_prompt="You are a helpful AI assistant answer questions accurately."
# )


# # --- PART 4: THE CHAT LOOP ---

# print("--- CLEAN THINKING AGENT ---")

# while True:
#     user_input = input("\n\033[94mYou: \033[0m") 
    
#     if user_input.lower() in ["exit", "quit"]:
#         break
    
#     try:
#         # Agent creates the response silently...
#         result = agent.invoke({
#             "messages": [{"role": "user", "content": user_input}]
#         })
        
#         # ...And we print ONLY the final result here
#         final_message = result["messages"][-1]
        
#         print(f"\n\033[96mFinal Answer:\n{final_message.content}\033[0m")
        
#     except Exception as e:
#         print(f"\033[91mError: {str(e)}\033[0m")