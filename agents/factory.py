import time
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_mistralai import ChatMistralAI
from agents.state import AgentState
from agents.rate_limiter import InMemoryRateLimiter
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from database.connection import get_collection
from datetime import datetime
from zoneinfo import ZoneInfo

def create_agent(
    agent_name: str,
    model_name: str,
    system_prompt_builder,
    tools: list,
    checkpointer,
    max_iterations: int = 10,
    rate_limit_min: int = 10,
    rate_limit_hour: int = 100,
    read_tool_names: list = None,
    write_tool_names: list = None,
) -> dict:
    """Factory to create a LangGraph agent with specific tools and configuration."""
    
    llm = ChatMistralAI(model=model_name, temperature=0)
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    read_names = set(read_tool_names or [])
    write_names = set(write_tool_names or [])
    
    read_tools = [t for t in tools if t.name in read_names]
    write_tools = [t for t in tools if t.name in write_names]
    
    # 1. Memory Manager Node (pre-LLM)
    async def memory_manager(state: AgentState):
        messages = state["messages"]
        total_chars = sum(len(str(m.content)) for m in messages)
        if total_chars > 25000 and len(messages) > 4:
            return {"messages": [SystemMessage(content=f"Il contesto è stato troncato per motivi di memoria. Mantieni il focus sulle ultime richieste.")] + messages[-3:]}
        return {}

    # 2. LLM Node
    async def call_model(state: AgentState, config):
        messages = list(state["messages"]) # Creiamo una copia per sicurezza
        
        # 1. Recuperiamo i dati freschi dal DB per costruire il System Prompt
        if agent_name == "segretario":
            uid = config.get("configurable", {}).get("user_id")
            col_utenti = await get_collection("utenti", uid)
            col_prog = await get_collection("programmazione", uid)
            oggi = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d")
            
            utenti_list = await col_utenti.find().to_list(100)
            agenda_list = await col_prog.find({"data": oggi}).to_list(50)
            
            sys_text = system_prompt_builder(utenti_list, agenda_list)
        else:
            # Per l'agente 'diario' non passiamo argomenti al builder
            sys_text = system_prompt_builder()
            
        sys_msg = SystemMessage(content=sys_text)
        
        # 2. Rimuoviamo eventuali SystemMessage precedenti per evitare conflitti o accumuli
        filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
            
        # 3. Invochiamo il modello (il system prompt viene prepeso al volo)
        response = await llm_with_tools.ainvoke([sys_msg] + filtered_messages)
        return {"messages": [response]}

    # 3. Router
    def should_continue(state: AgentState) -> str:
        messages = state["messages"]
        last_message = messages[-1]
        
        if not getattr(last_message, "tool_calls", None):
            return "end"
            
        # Sicurezza per loop infiniti (es. troppe chiamate tool consecutive)
        # Contiamo quanti AIMessage con tool_calls ci sono senza un HumanMessage in mezzo
        consecutive_tool_calls = 0
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                break
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                consecutive_tool_calls += 1
                
        if consecutive_tool_calls > max_iterations:
            return "end"
            
        has_write = any(tc["name"] in write_names for tc in last_message.tool_calls)
        
        if has_write:
            return "write_tools"
        elif last_message.tool_calls:
            return "read_tools"
            
        return "end"

    # Costruzione del grafo
    workflow = StateGraph(AgentState)
    workflow.add_node("memory", memory_manager)
    workflow.add_node("agent", call_model)
    
    if tools:
        # Usiamo tutti i tools per entrambi i nodi così in caso di chiamate miste il ToolNode non va in errore
        workflow.add_node("read_tools", ToolNode(tools))
        workflow.add_edge("read_tools", "agent")
        
        workflow.add_node("write_tools", ToolNode(tools))
        workflow.add_edge("write_tools", "agent")

    workflow.set_entry_point("memory")
    workflow.add_edge("memory", "agent")
    
    workflow.add_conditional_edges("agent", should_continue, {
        "read_tools": "read_tools" if tools else END,
        "write_tools": "write_tools" if tools else END,
        "end": END
    })

    # Compilazione
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["write_tools"] if write_tools else None
    )

    return {
        "name": agent_name,
        "graph": app,
        "rate_limiter": InMemoryRateLimiter(rate_limit_min, rate_limit_hour),
        "system_prompt_builder": system_prompt_builder
    }
