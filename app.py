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
        recency_weight = ((idx + 1) / total_rounds) ** 1.5 * 3.0
        scores[team] += recency_weight

    if len(history) >= 2:
        last_team = history[-1]
        transition_counts = defaultdict(Counter)
        for i in range(len(history) - 1):
            current_t = history[i]
            next_t = history[i+1]
            transition_counts[current_t][next_t] += 1
            
        if last_team in transition_counts:
            total_transitions = sum(transition_counts[last_team].values())
            if total_transitions > 0:
                for next_t, count in transition_counts[last_team].items():
                    prob = count / total_transitions
                    scores[next_t] += prob * 6.0

    last_seen_indices = {team: -1 for team in all_teams}
    for idx, team in enumerate(history):
        last_seen_indices[team] = idx
        
    for team in all_teams:
        if last_seen_indices[team] == -1:
            absence_duration = total_rounds
        else:
            absence_duration = total_rounds - 1 - last_seen_indices[team]
        scores[team] += (absence_duration * 0.35)

    for team in scores:
        if team in error_corrections:
            scores[team] += error_corrections[team] * 2.5

    total_score = sum(scores.values())
    if total_score > 0:
        percentages = {team: (score / total_score) * 100 for team, score in scores.items()}
    else:
        percentages = {team: (100.0 / len(all_teams)) for team in all_teams}
        
    sorted_preds = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    return sorted_preds

# عرض التوقيت المحلي
local_now = get_local_time()
st.info(f"🕒 التوقيت المحلي: **{local_now.strftime('%I:%M %p')}** | الصور تضغط تلقائياً لتوفير باقة الإنترنت:")

if 'last_processed_img' not in st.session_state:
    st.session_state.last_processed_img = None

# أداة رفع الصورة مع الضغط لتوفير الإنترنت والسرعة
uploaded_image = st.file_uploader("📥 ارفع لقطة الشاشة (يتم ضغطها فوراً):", type=["jpg", "jpeg", "png"])

if uploaded_image is not None:
    try:
        img = Image.open(uploaded_image)
        img.thumbnail((400, 400))
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=60)
        img_bytes = buf.getvalue()
        
        if img_bytes != st.session_state.last_processed_img:
            st.session_state.last_processed_img = img_bytes
            st.success("📉 تم ضغط الصورة ورفعها في أجزاء من الثانية! حدد الفريق الفائز أدناه بدقة:")
    except Exception:
        pass

# اختيار الفائز الحقيقي بسرعة
st.subheader("🏆 حدد الفريق الفائز في الصورة الحالية:")
cols = st.columns(2)
for i, team in enumerate(teams_list):
    with cols[i % 2]:
        if st.button(f"فاز: {team}", key=f"win_btn_{i}", use_container_width=True):
            if st.session_state.history:
                top_predicted_team = predict_next_team(st.session_state.history, st.session_state.time_logs, st.session_state.error_corrections)[0][0]
                if top_predicted_team != team:
                    st.session_state.error_corrections[team] += 2.0
                    st.warning(f"⚠️ تعلم متقدم: توقع النظام ({top_predicted_team}) والفائز الحقيقي ({team}).")
            
            st.session_state.history.append(team)
            st.session_state.time_logs.append(get_local_time().hour)
            save_memory_to_file(st.session_state.history, st.session_state.time_logs, st.session_state.error_corrections)
            st.success(f"تم تسجيل فوز {team} بنجاح!")
            st.rerun()

current_predictions = predict_next_team(st.session_state.history, st.session_state.time_logs, st.session_state.error_corrections)

st.divider()

if st.button("🗑️ مسح السجل والذاكرة بالكامل", key="reset_v5", use_container_width=True):
    st.session_state.history = []
    st.session_state.time_logs = []
    st.session_state.error_corrections = defaultdict(float)
    st.session_state.last_processed_img = None
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    st.rerun()

st.subheader(f"📊 سجل الجولات ({len(st.session_state.history)} جولة):")
if st.session_state.history:
    st.text(" ->
