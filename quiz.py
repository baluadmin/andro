import os
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from google import genai

# Page Configuration
st.set_page_config(page_title="PDF Quiz App with Gemini", page_icon="📚", layout="centered")

st.title("📚 PDF Quiz Assistant (Powered by Gemini)")
st.write("Select a PDF from your `my_documents` folder, test your knowledge, and get instant explanations!")

# Initialize Gemini Client using your provided API key
GEMINI_API_KEY = "AQ.Ab8RN6Jc2067GmNfKToB9XuTi3RA7Nok1yiCUgS-8zJJzKavBw"
client = genai.Client(api_key=GEMINI_API_KEY)

# Function to load PDFs from the local 'my_documents' folder
DOC_DIR = "my_documents"

@st.cache_data
def get_pdf_files():
    if not os.path.exists(DOC_DIR):
        os.makedirs(DOC_DIR)
        return []
    return [f for f in os.listdir(DOC_DIR) if f.endswith(".pdf")]

pdf_files = get_pdf_files()

if not pdf_files:
    st.error(f"No PDF files found in the '{DOC_DIR}' folder! Please upload your PDF files inside that folder on GitHub.")
    st.stop()

# Sidebar Selection
selected_pdf = st.sidebar.selectbox("Choose a PDF document", pdf_files)
pdf_path = os.path.join(DOC_DIR, selected_pdf)

@st.cache_data
def load_pdf_text(path):
    loader = PyPDFLoader(path)
    pages = loader.load()
    text = "".join([page.page_content for page in pages])
    return text

with st.spinner("Extracting text from PDF..."):
    pdf_text = load_pdf_text(pdf_path)

# Initialize Session State for Quiz Generation
if "quiz_data" not in st.session_state or st.session_state.get("current_pdf") != selected_pdf:
    st.session_state.current_pdf = selected_pdf
    st.session_state.quiz_data = None
    st.session_state.submitted = False

if st.button("Generate New Quiz"):
    with st.spinner("Generating quiz questions using Gemini..."):
        prompt = f"""
        Based on the following document text, generate 1 challenging multiple-choice question.
        Provide 4 options labeled A, B, C, and D.
        Specify the correct answer explicitly.
        Provide a detailed explanation for why the answer is correct.

        Format your output strictly in the following layout:
        QUESTION: [Your Question]
        A) [Option A]
        B) [Option B]
        C) [Option C]
        D) [Option D]
        CORRECT: [A/B/C/D]
        EXPLANATION: [Detailed explanation]

        Document text excerpt:
        {pdf_text[:4000]}
        """
        
        # Call Gemini model
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        st.session_state.quiz_data = response.text
        st.session_state.submitted = False

# Parse and display quiz if available
if st.session_state.quiz_data:
    raw_text = st.session_state.quiz_data
    
    try:
        opt_a, opt_b, opt_c, opt_d = "", "", "", ""
        correct_ans = "A"
        explanation_lines = []
        question_lines = []
        
        exp_collecting = False
        
        for line in raw_text.split("\n"):
            if line.startswith("QUESTION:"):
                question_lines.append(line.replace("QUESTION:", "").strip())
            elif line.startswith("A)"):
                opt_a = line.replace("A)", "").strip()
            elif line.startswith("B)"):
                opt_b = line.replace("B)", "").strip()
            elif line.startswith("C)"):
                opt_c = line.replace("C)", "").strip()
            elif line.startswith("D)"):
                opt_d = line.replace("D)", "").strip()
            elif line.startswith("CORRECT:"):
                correct_ans = line.replace("CORRECT:", "").strip()[0].upper()
            elif line.startswith("EXPLANATION:"):
                exp_collecting = True
                explanation_lines.append(line.replace("EXPLANATION:", "").strip())
            elif exp_collecting:
                explanation_lines.append(line.strip())

        question_text = " ".join(question_lines) if question_lines else "Question text parsing error."
        full_explanation = " ".join(explanation_lines)

        st.markdown("### 🧠 Pop Quiz")
        st.write(f"**{question_text}**")

        options = {
            "A": opt_a,
            "B": opt_b,
            "C": opt_c,
            "D": opt_d
        }

        user_choice = st.radio(
            "Select your option:",
            options=list(options.keys()),
            format_func=lambda x: f"{x}) {options[x]}"
        )

        if st.button("Submit Answer"):
            st.session_state.submitted = True

        if st.session_state.submitted:
            if user_choice == correct_ans:
                st.success("🎉 Good job! Your answer is correct.")
            else:
                st.error(f"❌ Wrong answer. The correct option was **{correct_ans}**.")
            
            st.info(f"**Explanation:** {full_explanation}")

    except Exception as e:
        st.error(f"Error parsing quiz format. Click generate again. Details: {e}")
