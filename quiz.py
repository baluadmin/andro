# -*- coding: utf-8 -*-
import os
import pypdf
from groq import Groq
import streamlit as st
import streamlit.components.v1 as components
import chromadb

st.set_page_config(page_title="AI Document Quiz Master", layout="centered")

# --- HIDE STREAMLIT HEADER, FOOTER & TOOLBARS ---
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stToolbar"] {display: none !important;}
div[data-testid="stDecoration"] {display: none !important;}
div[data-testid="stStatusWidget"] {display: none !important;}
.stAppDeployButton {display: none !important;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.title("🎯 AI Document Quiz Master (தமிழ்)")
st.write("உங்கள் ஃபோல்டரில் உள்ள ஆவணங்களிலிருந்து வரம்பற்ற கேள்விகளுடன் பயிற்சி செய்யுங்கள்!")

# 1. Folder & Database Setup
DOCS_FOLDER = "./my_documents"
db_path = "./chroma_docs_db"

if not os.path.exists(DOCS_FOLDER):
    os.makedirs(DOCS_FOLDER)

# Session State Initialization
if "ai_question" not in st.session_state:
    st.session_state.ai_question = ""
if "context_used" not in st.session_state:
    st.session_state.context_used = ""
if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = ""
if "text_pointer" not in st.session_state:
    st.session_state.text_pointer = 0
if "current_file" not in st.session_state:
    st.session_state.current_file = ""
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "persistent_error" not in st.session_state:
    st.session_state.persistent_error = ""

# 2. Groq & ChromaDB Setup (Using Streamlit Secrets safely)
try:
    groq_api_key = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=groq_api_key)
    
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="subject_books_library")
except Exception as e:
    st.session_state.persistent_error = f"அமைப்புப் பிழை (Setup Error): உங்கள் .streamlit/secrets.toml ஃபைலில் 'GROQ_API_KEY' சரியாக உள்ளதா எனச் சரிபார்க்கவும்."

if st.session_state.persistent_error:
    st.error(st.session_state.persistent_error)
    st.stop()

# Auto-load files from folder
def load_all_files():
    if not os.path.exists(DOCS_FOLDER):
        return []
    
    files = [f for f in os.listdir(DOCS_FOLDER) if f.endswith((".pdf", ".txt"))]
    if not files:
        sample_path = os.path.join(DOCS_FOLDER, "sample_doc.txt")
        if not os.path.exists(sample_path):
            with open(sample_path, "w", encoding="utf-8") as f:
                f.write("தமிழ்நாடு இந்தியாவின் தெற்கே உள்ள ஒரு மாநிலமாகும். இதன் தலைநகரம் சென்னை ஆகும்.")
        files = [f for f in os.listdir(DOCS_FOLDER) if f.endswith((".pdf", ".txt"))]

    for file in files:
        file_path = os.path.join(DOCS_FOLDER, file)
        try:
            existing = collection.get(ids=[file])
            if not existing or not existing["ids"]:
                text_content = ""
                if file.endswith(".pdf"):
                    reader = pypdf.PdfReader(file_path)
                    for page in reader.pages:
                        text_content += page.extract_text() or ""
                elif file.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        text_content = f.read()
                if text_content.strip():
                    collection.add(documents=[text_content], ids=[file])
        except Exception:
            pass
    return files

available_files = load_all_files()

# File Selection Dropdown
selected_file = st.selectbox("பயிற்சிக்கான ஆவணத்தைத் தேர்ந்தெடுக்கவும்:", available_files)

# Reset if file changes
if st.session_state.current_file != selected_file:
    st.session_state.current_file = selected_file
    st.session_state.text_pointer = 0
    st.session_state.question_count = 0
    st.session_state.ai_question = ""
    st.session_state.evaluation_result = ""
    st.session_state.persistent_error = ""

def generate_question():
    try:
        file_data = collection.get(ids=[selected_file])
        full_text = file_data["documents"][0] if file_data and file_data["documents"] else "பொதுவான தகவல்"
        total_len = len(full_text)
        
        if st.session_state.text_pointer >= total_len:
            st.session_state.text_pointer = 0
            
        chunk_size = 3500
        start_idx = st.session_state.text_pointer
        end_idx = min(start_idx + chunk_size, total_len)
        sample_text = full_text[start_idx:end_idx]
        st.session_state.text_pointer = end_idx
        
        prompt = f"""
        Create ONE multiple-choice question (MCQ) in pure, grammatically correct TAMIL based on this text.
        Structure:
        Question: [Question in Tamil]
        a. [Option A]
        b. [Option B]
        c. [Option C]
        d. [Option D]
        
        Text: {sample_text}
        """
        
        with st.spinner("கேள்வி உருவாக்கப்படுகிறது..."):
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
        
        st.session_state.ai_question = completion.choices[0].message.content
        st.session_state.context_used = sample_text
        st.session_state.question_count += 1
        st.session_state.evaluation_result = ""
        st.session_state.persistent_error = ""
    except Exception as e:
        st.session_state.persistent_error = f"கேள்வி உருவாக்குவதில் பிழை: {e}"

# Generate first question automatically if none exists yet
if not st.session_state.ai_question:
    if st.button("🚀 கேள்விகளைத் தொடங்குக"):
        generate_question()
        st.rerun()

# Display Persistent Errors if any
if st.session_state.persistent_error:
    st.error(st.session_state.persistent_error)

# Display Question
if st.session_state.ai_question:
    st.markdown(f"### 📊 வினா எண்: {st.session_state.question_count}")
    st.markdown(st.session_state.ai_question)
    
    user_choice = st.radio("உங்கள் விடையைத் தேர்ந்தெடுக்கவும்:", ("a", "b", "c", "d"), key=f"ans_{st.session_state.question_count}")
    
    if st.button("சமர்ப்பிக்கவும் ➡️"):
        try:
            eval_prompt = f"""
            Question & Options: {st.session_state.ai_question}
            Context: {st.session_state.context_used}
            User choice: '{user_choice}'
            Task (in correct TAMIL):
            - Check if correct. Start with "✅ **நன்று! (சரியான பதில்)**" or "❌ **தவறு! (தவறான பதில்)**".
            - Provide "**சரியான விளக்கம்:**" with the factual reason.
            """
            with st.spinner("மதிப்பிடப்படுகிறது..."):
                eval_comp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": eval_prompt}],
                    temperature=0.3
                )
            st.session_state.evaluation_result = eval_comp.choices[0].message.content
            st.session_state.persistent_error = ""
        except Exception as e:
            st.session_state.persistent_error = f"மதிப்பீட்டுப் பிழை: {e}"

    if st.session_state.evaluation_result:
        st.markdown("---")
        st.subheader("📢 மதிப்பீடு:")
        st.markdown(st.session_state.evaluation_result)
        
        if st.button("⏭️ அடுத்த கேள்வி"):
            generate_question()
            st.rerun()
