import streamlit as st
import numpy as np
import json
from collections import defaultdict, Counter

st.set_page_config(page_title="مساعد توقع الجولات الذكي", layout="centered")

st.title("⚽ نظام توقع الجولات (مع حفظ واستعادة الذاكرة)")
st.write("النظام المطور: يحفظ سجلك بالكامل ويتعلم من أخطائه مع إمكانية تصدير واستيراد الذاكرة!")

# تهيئة الذاكرة
if 'history' not in st.session_state:
    st.session_state.history = []
if 'error_corrections' not in st.session_state:
    st.session_state.error_corrections = defaultdict(float)

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

# قسم حفظ واستعادة السجل والذاكرة
st.sidebar.header("💾 إدارة الذاكرة والسجل")
if st.session_state.history:
    # تجهيز ملف JSON للتحميل
    save_data = {
        "history": st.session_state.history,
        "error_corrections": dict(st.session_state.error_corrections)
    }
    json_str = json.dumps(save_data, ensure_ascii=False, indent=4)
    st.sidebar.download_button(
        label="📥 تحميل السجل الحالي (حفظ)",
        data=json_str,
        file_name="game_predictor_memory.json",
        mime="application/json"
    )

uploaded_file = st.sidebar.file_uploader("📤 استرجاع سجل سابق (رفع ملف الذاكرة)", type=["json"])
if uploaded_file is not None:
    try:
        loaded_data = json.load(uploaded_file)
        st.session_state.history = loaded_data.get("history", [])
        st.session_state.error_corrections = defaultdict(float, loaded_data.get("error_corrections", {}))
        st.sidebar.success("تم استرجاع السجل والذاكرة بنجاح!")
        st.rerun()
    except Exception as e:
        st.sidebar.error("خطأ في قراءة الملف.")

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
            st.rerun()

if st.button("🗑️ مسح السجل وإعادة ضبط الذاكرة", use_container_width=True):
    st.session_state.history = []
    st.session_state.error_corrections = defaultdict(float)
    st.rerun()

st.divider()

st.subheader(f"📊 سجل الجولات ({len(st.session_state.history)} جولة):")
if st.session_state.history:
    st.text(" -> ".join(st.session_state.history[-15:]))
else:
    st.info("لم يتم تسجيل أي جولات بعد.")

st.subheader("🎯 توقعات الجولة القادمة:")
if len(st.session_state.history) >= 1:
    for team, prob in current_predictions:
        st.metric(label=team, value=f"{prob:.1f}%")
else:
    st.warning("أدخل جولة واحدة على الأقل لبدء تحليل التوقعات.")
