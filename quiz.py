# -*- coding: utf-8 -*-
import os
import random
import pypdf
from groq import Groq
import streamlit as st
import chromadb

st.set_page_config(page_title="AI Document Quiz Master", layout="centered")

st.title("🎯 AI Document Quiz Master (தமிழ்)")
st.write("உங்கள் ஆவணங்களிலிருந்து எப்பேர்ப்பட்ட பொதுவான வினாக்களையும் (MCQs) தமிழில் உருவாக்கிக் பயிற்சி செய்யுங்கள்!")

# 1. Folder & Database Setup
DOCS_FOLDER = "./my_documents"
db_path = "./chroma_docs_db"

if not os.path.exists(DOCS_FOLDER):
    os.makedirs(DOCS_FOLDER)

# 2. Groq & ChromaDB Setup (Free alternative to ChatGPT/Gemini)
try:
    groq_api_key = "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" 
    # Replace with your free Groq key from console.groq.com
    client = Groq(api_key=groq_api_key)
    
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

# 3. Dynamic File Selection
if not available_files:
    st.warning(f"⚠️ `{DOCS_FOLDER}` கோப்புறை காலியாக உள்ளது! GitHub ரிபாசிட்டரியில் `my_documents` என்ற ஃபோல்டரை உருவாக்கி அதற்குள் உங்கள் PDF அல்லது TXT கோப்புகளைச் சேர்த்துள்ளீர்களா என உறுதி செய்யவும்.")
    selected_file = "Sample"
else:
    selected_file = st.selectbox(
        "பயிற்சிக்கான ஆவணம் / தலைப்பைத் தேர்ந்தெடுக்கவும்:",
        available_files
    )

# Function to generate question in Tamil using Groq (Llama 3)
def generate_new_question():
    try:
        sample_text = "பொதுவான அறிவு மற்றும் ஆவணத் தகவல்."
        if available_files:
            file_data = collection.get(ids=[selected_file])
            if file_data and file_data["documents"]:
                full_text = file_data["documents"][0]
                start_idx = random.randint(0, max(0, len(full_text) - 4000))
                sample_text = full_text[start_idx:start_idx + 4000]
        
        prompt = f"""
        You are an expert quiz creator. Read the following text extracted strictly from the document and create ONE high-quality multiple-choice question (MCQ) in TAMIL language.
        
        CRITICAL INSTRUCTIONS:
        1. The question, options, and explanation MUST be completely in TAMIL (தமிழ்). Avoid using any LaTeX symbols or dollar signs ($).
        2. Put each option (a, b, c, d) on a completely new line. 
        3. Use this exact output structure:
        
        Question: [Type the question here in Tamil]
        
        a. [Option A text in Tamil]
        b. [Option B text in Tamil]
        c. [Option C text in Tamil]
        d. [Option D text in Tamil]
        
        Text Content:
        {sample_text}
        """
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        st.session_state.ai_question = completion.choices[0].message.content
        st.session_state.context_used = sample_text
        st.session_state.question_count += 1
        st.session_state.evaluation_result = ""
    except Exception as e:
        st.error(f"Error generating question: {e}")

# Start Quiz Button
st.markdown("---")
if st.button("🚀 வினாடி வினாவைத் தொடங்குக / அடுத்த கேள்வி"):
    generate_new_question()

# 4. Display Question and Options
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
                
                Reference context: {st.session_state.context_used}
                User selected option: '{user_choice}'
                
                Task (Completely in TAMIL / தமிழ்):
                - Check if the user's selected option is correct based on the reference context and options.
                - If correct, start with "✅ **நன்று! (சரியான பதில்)**" and appreciate the user in Tamil.
                - If incorrect, start with "❌ **தவறு! (தவறான பதில்)**", state what the correct option/answer is, and provide a short explanation in Tamil.
                """
                
                eval_completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": eval_prompt}],
                    temperature=0.5
                )
                
                st.session_state.evaluation_result = eval_completion.choices[0].message.content
            except Exception as e:
                st.error(f"Error evaluating: {e}")

    # Display Evaluation Result
    if st.session_state.evaluation_result:
        st.markdown("---")
        st.subheader("📢 AI மதிப்பீடு:")
        st.markdown(st.session_state.evaluation_result)
