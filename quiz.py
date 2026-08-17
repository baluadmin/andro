# -*- coding: utf-8 -*-
import os
import random
import pypdf
from google import genai
import streamlit as st
import chromadb

st.set_page_config(page_title="NEET Pattern AI Quiz Master", layout="centered")

st.title("🎯 NEET Pattern AI Quiz Master (தமிழ்)")
st.write("உங்கள் ஆவணங்களிலிருந்து வரம்பற்ற NEET-வடிவ வினாக்களை (MCQs, Statements, Assertion-Reasoning) தமிழில் பயிற்சி செய்யுங்கள்!")

# 1. Folder & Database Setup
DOCS_FOLDER = "./my_documents"
db_path = "./chroma_docs_db"

if not os.path.exists(DOCS_FOLDER):
    os.makedirs(DOCS_FOLDER)

# 2. Gemini & ChromaDB Setup
try:
    client = genai.Client(api_key="AQ.Ab8RN6Lq1AOV_J932ovPXEpNx6lsD95e91rF5UDC0GAtDNAfeQ")
    chroma_client = chromadb.PersistentClient(path=db_path)
    collection = chroma_client.get_or_create_collection(name="subject_books_library")
except Exception as e:
    st.error(f"Configuration Error: {e}")
    st.stop()

# Auto-load all files from folder into ChromaDB
def load_all_files():
    if not os.path.exists(DOCS_FOLDER):
        return []
    
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
        except Exception as e:
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
if "quiz_active" not in st.session_state:
    st.session_state.quiz_active = False
if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = ""
if "show_explanation_prompt" not in st.session_state:
    st.session_state.show_explanation_prompt = False
if "detailed_explanation" not in st.session_state:
    st.session_state.detailed_explanation = ""

# 3. Dynamic File/Subject Selection
if not available_files:
    st.warning(f"⚠️ `{DOCS_FOLDER}` கோப்புறைக்குள் எந்த PDF அல்லது TXT கோப்புகளும் கிடைக்கவில்லை! தயவுசெய்து உங்கள் படிப்பு ஆவணங்களை அங்கு சேர்க்கவும்.")
    st.stop()

selected_file = st.selectbox(
    "பயிற்சிக்கான ஆவணம் / தலைப்பைத் தேர்ந்தெடுக்கவும்:",
    available_files
)

# Function to generate NEET pattern question in Tamil
def generate_new_question():
    try:
        file_data = collection.get(ids=[selected_file])
        
        if not file_data or not file_data["documents"]:
            st.warning(f"மன்னிக்கவும்! `{selected_file}` கோப்பை தரவுத்தளத்திலிருந்து படிக்க முடியவில்லை.")
            return
        
        full_text = file_data["documents"][0]
        start_idx = random.randint(0, max(0, len(full_text) - 4000))
        sample_text = full_text[start_idx:start_idx + 4000]
        
        prompt = f"""
        You are an expert NEET question paper setter. Read the following text extracted strictly from '{selected_file}' and create ONE high-quality multiple-choice question in TAMIL language following the exact NEET exam patterns (such as Direct MCQs, Statement I & II type, or Assertion-Reasoning type).
        
        CRITICAL INSTRUCTIONS:
        1. The question, options, and explanation MUST be completely in TAMIL (தமிழ்). Avoid using any LaTeX symbols or dollar signs ($).
        2. Ensure clean formatting without awkward spacing, line wrapping breaks, or broken Tamil compound words.
        3. Put each option (a, b, c, d) on a completely new line. 
        4. Use this exact output structure:
        
        Question: [Type the NEET pattern question here in Tamil]
        
        a. [Option A text in Tamil]
        b. [Option B text in Tamil]
        c. [Option C text in Tamil]
        d. [Option D text in Tamil]
        
        Text Content:
        {sample_text}
        """
        
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt
        )
        
        st.session_state.ai_question = response.text
        st.session_state.context_used = sample_text
        st.session_state.question_count += 1
        st.session_state.quiz_active = True
        st.session_state.evaluation_result = ""
        st.session_state.show_explanation_prompt = False
        st.session_state.detailed_explanation = ""
    except Exception as e:
        st.error(f"Error: {e}")

# Start Quiz Button
if not st.session_state.quiz_active:
    if st.button("🚀 NEET வினாடி வினாவைத் தொடங்குக"):
        st.session_state.question_count = 0
        generate_new_question()
        st.rerun()

# 4. Display Question and Options
if st.session_state.quiz_active and st.session_state.ai_question:
    st.markdown("---")
    st.markdown(f"### 📊 வினா எண்: {st.session_state.question_count} (ஆவணம்: {selected_file})")
    
    # Using st.markdown instead of st.text for clean Tamil text formatting
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
                
                Reference context: {st.session_state.context_used}
                User selected option: '{user_choice}'
                
                Task (Completely in TAMIL / தமிழ்):
                - Check if the user's selected option is correct based on the reference context and options.
                - If correct, start with "✅ **நன்று! (சரியான பதில்)**" and appreciate the user in Tamil.
                - If incorrect, start with "❌ **தவறு! (தவறான பதில்)**", state what the correct option/answer is, and provide a short explanation in Tamil based on NEET standards. Ensure smooth formatting without broken compound words.
                """
                
                eval_response = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=eval_prompt
                )
                
                st.session_state.evaluation_result = eval_response.text
                st.session_state.show_explanation_prompt = True
            except Exception as e:
                st.error(f"Error: {e}")

    # Display Evaluation Result
    if st.session_state.evaluation_result:
        st.markdown("---")
        st.subheader("📢 AI மதிப்பீடு:")
        st.markdown(st.session_state.evaluation_result)
        
        # Ask for Detailed Explanation (Yes / No)
        if st.session_state.show_explanation_prompt and not st.session_state.detailed_explanation:
            st.markdown("---")
            st.write("💡 **இந்தக் கேள்விக்கு மேலும் விரிவான விளக்கம் தேவையா?**")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("ஆம் (விளக்கத்தைப் பெறுக)"):
                    with st.spinner("AI விரிவான விளக்கத்தை உருவாக்குகின்றது..."):
                        detail_prompt = f"""
                        Provide a deep, step-by-step detailed NEET-level explanation and concept background for this question completely in TAMIL (தமிழ்):
                        Question & Options: {st.session_state.ai_question}
                        Context: {st.session_state.context_used}
                        """
                        detail_response = client.models.generate_content(
                            model="gemini-3.5-flash-lite",
                            contents=detail_prompt
                        )
                        st.session_state.detailed_explanation = detail_response.text
                        st.rerun()
            with col2:
                if st.button("இல்லை (அடுத்த கேள்வி)"):
                    generate_new_question()
                    st.rerun()

        # Display Detailed Explanation and Next Question Button
        if st.session_state.detailed_explanation:
            st.markdown("---")
            st.subheader("📖 விரிவான விளக்கம்:")
            st.markdown(st.session_state.detailed_explanation)
            
            if st.button("👉 அடுத்த கேள்விக்கு இங்கே கிளிக் செய்யவும்"):
                generate_new_question()
                st.rerun()