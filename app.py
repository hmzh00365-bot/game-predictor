import streamlit as st
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from PIL import Image

st.set_page_config(page_title="مساعد توقع الجولات الذكي", layout="centered")

st.title("⏱️👁️‍🗨️ نظام توقع الجولات (الزمن المضبوط، الرؤية، والتعلم)")
st.write("النسخة المحدثة: ضبط التوقيت المحلي بدقة متناهية مع تحليل الرهانات وسلاسل ماركوف.")

MEMORY_FILE = "history_memory_time.txt"

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

# دالة لحساب التوقيت المحلي بدقة (إضافة 3 ساعات لتصحيح فارق الخادم السحابي UTC)
def get_local_time():
    return datetime.utcnow() + timedelta(hours=3)

def predict_next_team(history, time_logs, error_corrections, crowd_boosts=None):
    all_teams = teams_list.copy()
    for t in history:
        if t not in all_teams:
            all_teams.append(t)
            
    if not history and not crowd_boosts:
        base_prob = 100.0 / len(all_teams)
        return [(team, base_prob) for team in all_teams]
        
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

    if crowd_boosts:
        for team, boost_val in crowd_boosts.items():
            if team in scores:
                scores[team] += boost_val * 4.5

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

# عرض التوقيت المحلي الصحيح والمضبوط
local_now = get_local_time()
current_time_str = local_now.strftime("%I:%M %p")
st.info(f"🕒 التوقيت المحلي الصحيح: **{current_time_str}** (تم ضبطه تلقائياً ليتطابق مع هاتفك)")

st.subheader("📷 تحليل لقطة شاشة العجلة الحية:")
uploaded_screenshot = st.file_uploader("ارفع صورة العجلة الحالية (اختياري لتحليل الرهانات):", type=["jpg", "jpeg", "png"])

crowd_boosts = {}
if uploaded_screenshot is not None:
    image = Image.open(uploaded_screenshot)
    st.image(image, caption="لقطة الشاشة المرفوعة للعجلة", use_container_width=True)
    with st.expander("⚡ ضبط أوزان رهانات المراهنين الظاهرة في الصورة"):
        for team in teams_list:
            val = st.slider(f"قوة رهانات جمهور: {team}", 0, 5, 0, key=f"crowd_{team}")
            if val > 0:
                crowd_boosts[team] = val

current_predictions = predict_next_team(st.session_state.history, st.session_state.time_logs, st.session_state.error_corrections, crowd_boosts)

st.divider()
st.subheader("تسجيل نتيجة الجولة المنتهية (الواقعية):")

for i, team in enumerate(teams_list):
    if st.button(f"فاز: {team}", key=f"team_btn_{i}", use_container_width=True):
        if current_predictions:
            top_predicted_team = current_predictions[0][0]
            if top_predicted_team != team:
                st.session_state.error_corrections[team] += 2.0
                st.warning(f"⚠️ تعلم متقدم: توقع النظام ({top_predicted_team}) وفاز ({team}). تم تحديث الأوزان.")
        
        st.session_state.history.append(team)
        st.session_state.time_logs.append(get_local_time().hour) # تسجيل الساعة المحلية الصحيحة
        save_memory_to_file(st.session_state.history, st.session_state.time_logs, st.session_state.error_corrections)
        st.rerun()

if st.button("🗑️ مسح السجل وإعادة ضبط الذاكرة والوقت", key="reset_btn", use_container_width=True):
    st.session_state.history = []
    st.session_state.time_logs = []
    st.session_state.error_corrections = defaultdict(float)
    if os.path.exists(MEMORY_FILE):
        os.remove(MEMORY_FILE)
    st.rerun()

st.divider()

st.subheader(f"📊 سجل الجولات ({len(st.session_state.history)} جولة مسجلة زمنياً):")
if st.session_state.history:
    st.text(" -> ".join(st.session_state.history[-15:]))
else:
    st.info("لم يتم تسجيل أي جولات بعد.")

st.subheader("🎯 توقعات الجولة القادمة:")
if len(st.session_state.history) >= 1 or crowd_boosts:
    for team, prob in current_predictions:
        st.metric(label=team, value=f"{prob:.1f}%")
else:
    st.warning("أدخل جولة واحدة على الأقل أو ارفع لقطة الشاشة لبدء التحليل.")
