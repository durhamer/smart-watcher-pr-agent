# utils.py
import re

class StreamToExpander:
    """攔截系統標準輸出 (stdout)，將其轉向 Streamlit 的 Expander 元件中"""
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        self.text_area = self.expander.empty()

    def write(self, data):
        # 👉 核心修復：遇到 CrewAI 的底層警告，我們直接「已讀不回」，不印在畫面上！
        if "[CrewAIEventsBus]" in data or "Sync handler error" in data:
            return
            
        # 清除終端機專用的 ANSI 顏色代碼
        clean_data = re.sub(r'\x1b\[[0-9;]*m', '', data)
        self.buffer.append(clean_data)
        self.text_area.code("".join(self.buffer), language="text")

    def flush(self): 
        pass

# (原本下方的 clear_crewai_events 函數已經功成身退，可以直接刪除！)
