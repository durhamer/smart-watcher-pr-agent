# utils.py
import re

class StreamToExpander:
    """攔截系統標準輸出 (stdout)，將其轉向 Streamlit 的 Expander 元件中"""
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        self.text_area = self.expander.empty()

    def write(self, data):
        # 清除終端機專用的 ANSI 顏色代碼
        clean_data = re.sub(r'\x1b\[[0-9;]*m', '', data)
        self.buffer.append(clean_data)
        self.text_area.code("".join(self.buffer), language="text")

    def flush(self): 
        pass

def clear_crewai_events():
    """防彈版清除機制：強制洗掉 CrewAI 廣播中心的舊記憶，防止 Log 疊加與網頁當機"""
    try:
        from crewai.events.event_bus import crewai_event_bus
    except ModuleNotFoundError:
        try:
            from crewai.utilities.events import crewai_event_bus
        except ModuleNotFoundError:
            crewai_event_bus = None
            
    if crewai_event_bus and hasattr(crewai_event_bus, '_handlers'):
        crewai_event_bus._handlers.clear()
