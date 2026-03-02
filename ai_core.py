# ai_core.py
import os
import ast
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import FileReadTool, SerperDevTool
from langchain_google_genai import ChatGoogleGenerativeAI
from agents import AGENT_ROSTER

def evaluate_pipeline(user_post, selected_agent_keys, api_key):
    """呼叫架構師大腦，檢查邏輯並預估 Token"""
    os.environ["GOOGLE_API_KEY"] = api_key
    
    reviewer_llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview", 
        temperature=0.2,
        api_key=api_key
    )

    pipeline_str = " ➡️ ".join([AGENT_ROSTER[k]['role'] for k in selected_agent_keys])
    roles_desc = "\n".join([f"- {AGENT_ROSTER[k]['role']}: {AGENT_ROSTER[k]['goal']}" for k in selected_agent_keys])

    prompt = f"""
    你是一位資深的 AI 系統架構師。使用者安排了一個 Multi-Agent 流水線來處理以下任務：
    「{user_post}」

    使用者安排的執行順序是：
    {pipeline_str}

    各 Agent 職責：
    {roles_desc}

    請以繁體中文，在 150 字以內評估這個順序是否合理。
    如果邏輯完美，請大力稱讚。如果邏輯顛倒（如先寫作後分析），請幽默點出盲點並建議正確順序。
    """
    
    response = reviewer_llm.invoke(prompt)
    raw_content = response.content
    
    # 過濾 Gemini 3 Preview 格式
    final_text = raw_content
    if isinstance(raw_content, list) and len(raw_content) > 0:
        final_text = raw_content[0].get("text", str(raw_content))
    elif isinstance(raw_content, str) and raw_content.startswith("[{'type':"):
        try:
            parsed = ast.literal_eval(raw_content)
            final_text = parsed[0].get("text", raw_content)
        except: pass
        
    # 計算基礎 Token
    base_text = prompt + "".join([str(AGENT_ROSTER[k]) for k in selected_agent_keys])
    base_tokens = reviewer_llm.get_num_tokens(base_text)
    
    return final_text, base_tokens

def execute_crew(user_post, selected_agent_keys, api_key, serper_api_key):
    """正式組裝並啟動 CrewAI 團隊，回傳結果與帳單"""
    os.environ["GEMINI_API_KEY"] = api_key
    os.environ["GOOGLE_API_KEY"] = api_key
    os.environ["SERPER_API_KEY"] = serper_api_key
    
    llm = LLM(model="gemini/gemini-2.5-flash-lite", temperature=0.6, api_key=api_key)
    guidelines_tool = FileReadTool(file_path='pr_guidelines.txt')
    search_tool = SerperDevTool()

    active_agents = []
    active_tasks = []

    for key in selected_agent_keys:
        config = AGENT_ROSTER[key]
        
        agent_tools = []
        if config['needs_search']: agent_tools.append(search_tool)
        if config['needs_guidelines']: agent_tools.append(guidelines_tool)
        
        agent = Agent(
            role=config['role'],
            goal=config['goal'],
            backstory=config['backstory'],
            tools=agent_tools,
            allow_delegation=False,
            verbose=True,
            llm=llm
        )
        active_agents.append(agent)
        
        task = Task(
            description=config['task_desc'].format(post=user_post),
            expected_output=config['expected_output'],
            agent=agent
        )
        active_tasks.append(task)

    # ai_core.py 的下方
    pr_crew = Crew(
        agents=active_agents,
        tasks=active_tasks,
        process=Process.sequential,
        verbose=True  # 👉 就是少了這行！這行是開啟團隊廣播器的總開關
    )

    result = pr_crew.kickoff()
    usage = pr_crew.usage_metrics
    
    # 防彈版 Token 抓取
    prompt_t = usage.prompt_tokens if hasattr(usage, 'prompt_tokens') else usage.get("prompt_tokens", 0)
    comp_t = usage.completion_tokens if hasattr(usage, 'completion_tokens') else usage.get("completion_tokens", 0)
    total_t = usage.total_tokens if hasattr(usage, 'total_tokens') else usage.get("total_tokens", 0)
    
    metrics = {
        "prompt_tokens": prompt_t,
        "completion_tokens": comp_t,
        "total_tokens": total_t
    }
    
    return result.raw, metrics
