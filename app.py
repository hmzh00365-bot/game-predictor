import streamlit as st
import numpy as np
import json
import os
from collections import defaultdict, Counter

st.set_page_config(page_title="مساعد توقع الجولات الذكي", layout="centered")

st.title("⚽ نظام توقع الجولات (حفظ تلقائي للملفات)")
st.write("النظام المطور: يحفظ السجل والذاكرة تلقائياً في ملف نصي داخلي ليعود مستمراً دائماً.")

MEMORY_FILE = "history_memory.txt"

# دالة لقراءة الذاكرة تلقائياً من الملف النصي الداخلي
def load_memory_from_file():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                history = data.get("history", [])
                error_corrections = defaultdict(float, data.get("error_corrections", {}))
                return history, error_corrections
        except Exception:
            pass
    return [], defaultdict(float)

# دالة لحفظ الذاكرة تلقائياً في الملف النصي الداخلي
def save_memory_to_file(history, error_corrections):
    try:
        data = {
            "history": history,
            "error_corrections": dict(error_corrections)
        }
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# تهيئة الذاكرة عند بدء التشغيل وسحبها من الملف تلقائياً
if 'history' not in st.session_state or 'error_corrections' not in st.session_state:
    loaded_history, loaded_corrections = load_memory_from_file()
    st.session_state.history = loaded_history
    st.session_state.error_corrections = loaded_corrections

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

def predict_next_team(history, error_corrections):
    all_teams = teams_list.copy()
    for t in history:
        if t not in all_teams:
            all_teams.append(t)
            
    if not history:
        base_prob = 100.0 / len(all_teams)
        return [(team, base_prob) for team in all_teams]
        
    total_rounds = len(history)
    scores = {team: 1.0 for team in all_teams}
    
    for idx, team in enumerate(history):
        recency_weight = ((idx + 1) / total_rounds) ** 1.5 * 3.0
        scores[team] += recency_weight

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

current_predictions = predict_next_team(st.session_state.history, st.session_state.error_corrections)

st.subheader("تسجيل نتيجة الجولة المنتهية (الواقعية):")
cols = st.columns(2)

for i, team in enumerate(teams_list):
    with cols[i % 2]:
        if st.button(f"فاز: {team}", key=f"btn_{i}", use_container_width=True):
            if current_predictions:
                top_predicted_team = current_predictions[0][0]
                if top_predicted_team != team:
                    st.session_state.error_corrections[team] += 2.0
                    st.info(f"⚠️ تعلم متقدم: توقع النظام ({top_predicted_team}) والنتيجة كانت ({team}).")
            
            st.session_state.history.append(team)
            # حفظ تلقائي فوري في الملف النصي الداخلي عند كل إدخال
            save_memory_to_file(st.session_state.history, st.session_state.error_corrections)
            st.rerun()

if st.button("🗑️ مسح السجل وإعادة ضبط الذاكرة", use_container_width=True):
    st.session_state.history = []
    st.session_state.error_corrections = defaultdict(float)
    # مس
