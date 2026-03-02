# utils.py
import re
import sys

class StreamToExpander:
    """攔截系統標準輸出，轉向 Streamlit，並同步保留給後台"""
    def __init__(self, expander):
        self.expander = expander
        self.buffer = []
        self.text_area = self.expander.empty()

    def write(self, data):
        # 備份一份到原本的終端機，確保伺服器後台還是看得到完整 Log
        sys.__stdout__.write(data)
        
        # 👉 精準過濾：只擋掉那兩個討厭的報錯，其他通通放行！
        if "Sync handler error" in data or "Event pairing mismatch" in data:
            return
            
        # 清除終端機專用的顏色亂碼
        clean_data = re.sub(r'\x1b\[[0-9;]*m', '', data)
        self.buffer.append(clean_data)
        
        # 顯示在網頁上
        self.text_area.code("".join(self.buffer), language="text")

    def flush(self): 
        sys.__stdout__.flush()
