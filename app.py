import streamlit as st
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from PIL import Image
import io

st.set_page_config(page_title="مساعد توقع الجولات الذكي", layout="centered")

st.title("⚡ نظام التوقع السريع (تصحيح النتائج والرفع الخفيف)")
st.write("النسخة المحدثة: ضغط الصورة فوراً واختيار الفريق الفائز من القائمة بلمح البصر لتفادي الأخطاء.")

MEMORY_FILE = "history_memory_v5.txt"

def load_memory_from_file():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                history = data.get("history", [])
                time_logs = data.get("time_logs", [])
                error_corrections = defaultdict(float, data.get("error_corrections", {}))
                return history, time_logs, error_corrections
        except Exception:
            pass
    return [], [], defaultdict(float)

def save_memory_to_file(history, time_logs, error_corrections):
    try:
        data = {
            "history": history,
            "time_logs": time_logs,
            "error_corrections": dict(error_corrections)
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

if 'history' not in st.session_state or 'time_logs' not in st.session_state or 'error_corrections' not in st.session_state:
    h, t, c = load_memory_from_file()
    st.session_state.history = h
    st.session_state.time_logs = t
    st.session_state.error_corrections = c

teams_list = [
    "غلطة سراي", 
    "الأهلي المصري", 
    "النصر", 
    "الشباب", 
    "الاتحاد", 
    "الأهلي السعودي", 
    "العين", 
    "فنربخشة"
]

def get_local_time():
    return datetime.utcnow() + timedelta(hours=3)

def predict_next_team(history, time_logs, error_corrections):
    all_teams = teams_list.copy()
    for t in history:
        if t not in all_teams:
            all_teams.append(t)
            
    if not history:
        base_prime = 100.0 / len(all_teams)
        return [(team, base_prime) for team in all_teams]
        
    total_rounds = len(history) if history else 1
    scores = {team: 1.0 for team in all_teams}
    
    current_hour = get_local_time().hour
    if time_logs:
        for team, log_hour in zip(history, time_logs):
            if abs(current_hour - log_hour) <= 1 or abs(current_hour - log_hour) >= 23:
                scores[team] += 1.5

    for idx, team in enumerate(history):
        recency_weight = ((
