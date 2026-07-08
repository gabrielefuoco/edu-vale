from langchain_core.messages import AIMessage

responses = []

def set_next_llm_response(msg: AIMessage):
    responses.append(msg)
