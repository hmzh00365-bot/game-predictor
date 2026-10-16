import streamlit as st
import numpy as np
from collections import defaultdict, Counter

st.set_page_config(page_title="مساعد توقع الجولات الذكي", layout="centered")

st.title("⚽ نظام توقع الجولات (دوري أبطال أوروبا)")
st.write("النظام الذكي لتوقع نتائج الجولات والتعلم التكيفي من الأخطاء بناءً على الأندية الحقيقية.")

if 'history' not in st.session_state:
    st.session_state.history = []
if 'error_corrections' not in st.session_state:
    st.session_state.error_corrections = defaultdict(float)

# الأندية الثمانية المطابقة للصورة تماماً
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
    if not history:
        return []
        
    total_rounds = len(history)
    teams = list(set(history + list(error_corrections.keys())))
    scores = {team: 0.0 for team in teams}
    
    for idx, team in enumerate(history):
        weight = ((idx + 1) / total_rounds) * 2.0
        scores[team] += weight

    last_team = history[-1]
    transition_counts = defaultdict(Counter)
    for i in range(len(history) - 1):
        current_t = history[i]
        next_t = history[i+1]
        transition_counts[current_t][next_t] += 1
        
    if last_team in transition_counts:
        total_transitions = sum(transition_counts[last_team].values())
        for next_t, count in transition_counts[last_team].items():
            prob = count / total_transitions
            scores[next_t] += prob * 4.0

    last_seen_indices = {team: idx for idx, team in enumerate(history)}
    for team in teams:
        if team in last_seen_indices:
            absence_duration = total_rounds - 1 - last_seen_indices[team]
            scores[team] += (absence_duration * 0.15)

    for team in scores:
        if team in error_corrections:
            scores[team] += error_corrections[team]

    total_score = sum(scores.values())
    if total_score > 0:
        percentages = {team: (score / total_score) * 100 for team, score in scores.items()}
    else:
        percentages = {team: 0 for team in scores}
        
    sorted_preds = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    return sorted_preds

current_predictions = predict_next_team(st.session_state.history, st.session_state.error_corrections)

st.subheader("تسجيل نتيجة الجولة المنتهية:")
cols = st.columns(2)

for i, team in enumerate(teams_list):
    with cols[i % 2]:
        if st.button(f"فاز: {team}", key=f"btn_{i}", use_container_width=True):
            if current_predictions:
                top_predicted_team = current_predictions[0][0]
                if top_predicted_team != team:
                    st.session_state.error_corrections[team] += 1.5
                    st.info(f"⚠️ النظام تعلم من خطأه: توقع سابقاً {top_predicted_team} وفاز {team}.")
            
            st.session_state.history.append(team)
            st.rerun()

if st.button("🗑️ مسح السجل وإعادة الذاكرة", use_container_width=True):
    st.session_state.history = []
    st.session_state.error_corrections = defaultdict(float)
    st.rerun()

st.divider()

st.subheader(f"📊 سجل الجولات ({len(st.session_state.history)} جولة):")
if st.session_state.history:
    st.text(" -> ".join(st.session_state.history))
else:
    st.info("لم يتم تسجيل أي جولات بعد.")

st.subheader("🎯 توقعات الجولة القادمة:")
if len(st.session_state.history) >= 2:
    for team, prob in current_predictions:
        st.metric(label=team, value=f"{prob:.1f}%")
else:
    st.warning("أدخل على الأقل جولتين لتفعيل الخوارزمية.")
