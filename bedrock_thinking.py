import os
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, AIMessageChunk
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# ==============================================================================
# 1. SETUP
# ==============================================================================
llm = ChatBedrockConverse(
    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0", 
    region_name="us-east-1",
    max_tokens=8192,
    additional_model_request_fields={
        "thinking": { "type": "enabled", "budget_tokens": 4096 }
    }
)

memory = MemorySaver()
agent = create_react_agent(model=llm, tools=[], checkpointer=memory)

# ==============================================================================
# 2. STREAMING FUNCTION (Targeted & Efficient)
# ==============================================================================
def process_stream(user_input: str, thread_id: str = "1"):
    print(f"\n\033[94m💬 You: {user_input}\033[0m\n")
    
    response_stream = agent.stream(
        {"messages": [HumanMessage(content=user_input)]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="messages"
    )

    current_section = None 

    for chunk, metadata in response_stream:
        if not isinstance(chunk, AIMessageChunk): continue
        
        content = chunk.content
        
        # Case A: Simple String (Fallback)
        if isinstance(content, str):
            if current_section != "answer":
                print("\n\033[92m", end="") 
                current_section = "answer"
            print(content, end="", flush=True)
            continue

        # Case B: List of Blocks (The Bedrock Structure)
        for block in content:
            
            # --- 1. EXTRACT REASONING (Based on your Debug Output) ---
            # Structure: {'reasoning_content': {'text': '...'}}
            if "reasoning_content" in block:
                val = block["reasoning_content"].get("text", "")
                
                if val:
                    if current_section != "thought":
                        print("\033[90mDOC: ", end="") 
                        current_section = "thought"
                    print(val, end="", flush=True)
                continue

            # --- 2. EXTRACT FINAL ANSWER ---
            # Structure: {'text': '...'}
            if "text" in block:
                val = block["text"]
                
                if val:
                    if current_section != "answer":
                        print("\033[0m\n\n\033[92m", end="") 
                        current_section = "answer"
                    print(val, end="", flush=True)

    print("\033[0m\n")

# ==============================================================================
# 3. MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    print("✅ Agent Started (Final Clean Version)")
    while True:
        try:
            u_in = input("Input: ")
            if u_in.lower() in ["exit", "quit"]: break
            process_stream(u_in)
        except Exception as e:
            # We catch errors gracefully so the agent doesn't crash entirely
            print(f"\n❌ Error: {e}")