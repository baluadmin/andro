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
st.write("உங்கள் ஆவணத்திலிருந்து முழுமையான PDF-ஐ உள்ளடக்கும் வகையில் வரம்பற்ற கேள்விகளுடன் பயிற்சி செய்யுங்கள்!")

# 1. Folder & Database Setup
DOCS_FOLDER = "./my_documents"
db_path = "./chroma_docs_db"

if not os.path.exists(DOCS_FOLDER):
    os.makedirs(DOCS_FOLDER)

# 2. Groq & ChromaDB Setup
try:
    groq_api_key = "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"
    client = Groq(api_key=groq_api_key)
    
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="subject_books_library")
except Exception:
    st.error("மன்னிக்கவும், அமைப்புப் பிழை ஏற்பட்டுள்ளது. பிறகு முயற்சிக்கவும்.")
    st.stop()

# Auto-load all files from folder into ChromaDB
def load_all_files():
    if not os.path.exists(DOCS_FOLDER):
        return []
    
    files = [f for f in os.listdir(DOCS_FOLDER) if f.endswith((".pdf", ".txt"))]
    
    if not files:
        sample_file_path = os.path.join(DOCS_FOLDER, "sample_doc.txt")
        if not os.path.exists(sample_file_path):
            with open(sample_file_path, "w", encoding="utf-8") as sf:
                sf.write("தமிழ்நாடு (Tamil Nadu) இந்தியாவின் தெற்கே உள்ள ஒரு மாநிலமாகும். இதன் தலைநகரம் சென்னை ஆகும்.")
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

# Session State Initialization
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
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

# 3. Dynamic File Selection
if not available_files:
    st.warning(f"⚠️ `{DOCS_FOLDER}` கோப்புறை காலியாக உள்ளது.")
    selected_file = "Sample"
else:
    selected_file = st.selectbox(
        "பயிற்சிக்கான ஆவணம் / தலைப்பைத் தேர்ந்தெடுக்கவும்:",
        available_files
    )

if st.session_state.current_file != selected_file:
    st.session_state.current_file = selected_file
    st.session_state.text_pointer = 0
    st.session_state.question_count = 0
    st.session_state.ai_question = ""
    st.session_state.evaluation_result = ""

def generate_next_question():
    try:
        sample_text = "பொதுவான அறிவு மற்றும் ஆவணத் தகவல்."
        if available_files:
            file_data = collection.get(ids=[selected_file])
            if file_data and file_data["documents"]:
                full_text = file_data["documents"][0]
                total_len = len(full_text)
                
                if st.session_state.text_pointer >= total_len:
                    st.success("🎉 வாழ்த்துகள்! இந்த ஆவணத்தின் அனைத்துப் பகுதிகளிலிருந்தும் கேள்விகள் கேட்கப்பட்டுவிட்டன.")
                    st.session_state.text_pointer = 0
                
                chunk_size = 3500
                start_idx = st.session_state.text_pointer
                end_idx = min(start_idx + chunk_size, total_len)
                
                sample_text = full_text[start_idx:end_idx]
                st.session_state.text_pointer = end_idx
        
        prompt = f"""
        You are an expert Tamil quiz creator. Read the following progressive text block from the document and create ONE high-quality multiple-choice question (MCQ) strictly in pure, grammatically correct TAMIL (தமிழ்) language with zero spelling mistakes.
        
        CRITICAL FORMATTING INSTRUCTIONS:
        1. Ensure correct spelling and clear formatting in Tamil words. Do not make typo errors.
        2. Put each option (a, b, c, d) on a completely new line (one by one).
        3. Use this exact output structure:
        
        Question: [Type the question here cleanly in Tamil]
        
        a. [Option A text in Tamil]
        b. [Option B text in Tamil]
        c. [Option C text in Tamil]
        d. [Option D text in Tamil]
        
        Text Content Excerpt:
        {sample_text}
        """
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        
        st.session_state.ai_question = completion.choices[0].message.content
        st.session_state.context_used = sample_text
        st.session_state.question_count += 1
        st.session_state.evaluation_result = ""
    except Exception:
        st.error("கேள்வி உருவாக்குவதில் சிக்கல் ஏற்பட்டுள்ளது. மீண்டும் முயற்சிக்கவும்.")

if st.session_state.question_count == 0:
    st.markdown("---")
    if st.button("🚀 வினாடி வினாவைத் தொடங்குக"):
        with st.spinner("கேள்வி உருவாக்கப்படுகிறது..."):
            generate_next_question()
        st.rerun()

if st.session_state.ai_question:
    st.markdown(f"### 📊 வினா எண்: {st.session_state.question_count}")
    st.markdown(st.session_state.ai_question)
    
    user_choice = st.radio(
        "உங்கள் விடை விருப்பத்தைத் தேர்ந்தெடுக்கவும்:",
        ("a", "b", "c", "d"),
        key=f"q_{st.session_state.question_count}"
    )
    
    if st.button("சமர்ப்பித்து மதிப்பிடுக ➡️"):
        with st.spinner("AI உங்கள் பதிலைச் சரிபார்க்கிறது..."):
            try:
                eval_prompt = f"""
                Full Question and Options:
                {st.session_state.ai_question}
                
                Reference context from PDF: {st.session_state.context_used}
                User selected option: '{user_choice}'
                
                Task (Completely in correct TAMIL / தமிழ் with no spelling errors):
                - Check if the selected option '{user_choice}' is correct based on the text.
                - If correct, start with "✅ **நன்று! (சரியான பதில்)**".
                - If incorrect, start with "❌ **தவறு! (தவறான பதில்)**".
                - Provide a section "**சரியான விளக்கம்:**" that gives ONLY the direct fact or logic from the text. 
                - EXCLUDE meta phrases like "கொடுக்கப்பட்ட PDF-இல்" or "என குறிப்பிடப்பட்டுள்ளது". Just state the factual reason clearly and simply.
                """
                
                eval_completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": eval_prompt}],
                    temperature=0.3
                )
                
                st.session_state.evaluation_result = eval_completion.choices[0].message.content
            except Exception:
                st.error("மதிப்பீடு செய்வதில் சிக்கல் ஏற்பட்டுள்ளது.")

    if st.session_state.evaluation_result:
        st.markdown("---")
        st.subheader("📢 AI மதிப்பீடு மற்றும் தெளிவான விளக்கம்:")
        st.markdown(st.session_state.evaluation_result)
        
        components.html(
            """
            <script>
                const elements = window.parent.document.querySelectorAll('h3');
                elements.forEach(el => {
                    if (el.innerText.includes('மதிப்பீடு')) {
                        el.scrollIntoView({ behavior: 'smooth' });
                    }
                });
            </script>
            """,
            height=0
        )
        
        st.markdown("---")
        if st.button("⏭️ அடுத்த கேள்விக்குச் செல்க (Next Question)"):
            generate_next_question()
            st.rerun()
