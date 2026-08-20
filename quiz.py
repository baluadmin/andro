# -*- coding: utf-8 -*-

import os
import random
import pypdf
import streamlit as st
import chromadb
from google import genai


# ============================================================
# STREAMLIT PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="AI Document Quiz Master",
    page_icon="🎯",
    layout="centered"
)

st.title("🎯 AI Document Quiz Master (தமிழ்)")

st.write(
    "உங்கள் ஆவணங்களிலிருந்து பொதுவான வினாக்களையும் "
    "(MCQs) தமிழில் உருவாக்கிப் பயிற்சி செய்யுங்கள்!"
)


# ============================================================
# 1. FOLDER & CHROMADB SETUP
# ============================================================

DOCS_FOLDER = "./my_documents"
DB_PATH = "./chroma_docs_db"

if not os.path.exists(DOCS_FOLDER):
    os.makedirs(DOCS_FOLDER)


# ============================================================
# 2. GEMINI API SETUP
# ============================================================

try:

    # --------------------------------------------------------
    # Get Gemini API key from Streamlit Secrets
    # --------------------------------------------------------
    if "GEMINI_API_KEY" not in st.secrets:
        st.error(
            "❌ GEMINI_API_KEY கிடைக்கவில்லை.\n\n"
            "Streamlit → Settings → Secrets சென்று "
            "GEMINI_API_KEY சேர்க்கவும்."
        )
        st.stop()

    api_key = st.secrets["AQ.Ab8RN6Jc2067GmNfKToB9XuTi3RA7Nok1yiCUgS-8zJJzKavBw"]

    if not api_key:
        st.error("❌ GEMINI_API_KEY காலியாக உள்ளது.")
        st.stop()

    # --------------------------------------------------------
    # New Google Gemini SDK
    # --------------------------------------------------------
    client = genai.Client(api_key=api_key)

    # --------------------------------------------------------
    # ChromaDB
    # --------------------------------------------------------
    chroma_client = chromadb.PersistentClient(
        path=DB_PATH
    )

    collection = chroma_client.get_or_create_collection(
        name="subject_books_library"
    )

except Exception as e:

    st.error(
        f"❌ Configuration Error:\n\n{e}"
    )

    st.stop()


# ============================================================
# 3. LOAD PDF / TXT FILES INTO CHROMADB
# ============================================================

def load_all_files():

    if not os.path.exists(DOCS_FOLDER):
        return []

    files = [
        f for f in os.listdir(DOCS_FOLDER)
        if f.lower().endswith((".pdf", ".txt"))
    ]

    for file in files:

        file_path = os.path.join(
            DOCS_FOLDER,
            file
        )

        try:

            # Check whether file already exists
            existing = collection.get(
                ids=[file]
            )

            if existing and existing.get("ids"):
                continue

            text_content = ""

            # ------------------------------------------------
            # PDF
            # ------------------------------------------------

            if file.lower().endswith(".pdf"):

                reader = pypdf.PdfReader(
                    file_path
                )

                for page in reader.pages:

                    page_text = page.extract_text()

                    if page_text:
                        text_content += page_text + "\n"

            # ------------------------------------------------
            # TXT
            # ------------------------------------------------

            elif file.lower().endswith(".txt"):

                with open(
                    file_path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    text_content = f.read()

            # ------------------------------------------------
            # Add to ChromaDB
            # ------------------------------------------------

            if text_content.strip():

                collection.add(
                    documents=[text_content],
                    ids=[file]
                )

        except Exception as e:

            st.warning(
                f"⚠️ {file} load செய்ய முடியவில்லை: {e}"
            )

    return files


available_files = load_all_files()


# ============================================================
# 4. SESSION STATE
# ============================================================

if "question_count" not in st.session_state:
    st.session_state.question_count = 0

if "ai_question" not in st.session_state:
    st.session_state.ai_question = ""

if "context_used" not in st.session_state:
    st.session_state.context_used = ""

if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = ""

if "detailed_explanation" not in st.session_state:
    st.session_state.detailed_explanation = ""


# ============================================================
# 5. FILE SELECTION
# ============================================================

if not available_files:

    st.warning(
        f"⚠️ `{DOCS_FOLDER}` கோப்புறை காலியாக உள்ளது!\n\n"
        "GitHub repository-ல் `my_documents` என்ற folder உருவாக்கி "
        "PDF அல்லது TXT files சேர்க்கவும்."
    )

    selected_file = "Sample"

else:

    selected_file = st.selectbox(
        "📚 பயிற்சிக்கான ஆவணம் / தலைப்பைத் தேர்ந்தெடுக்கவும்:",
        available_files
    )


# ============================================================
# 6. GEMINI QUESTION GENERATION
# ============================================================

def generate_new_question():

    try:

        sample_text = (
            "பொதுவான அறிவு மற்றும் "
            "ஆவணத் தகவல்."
        )

        # ----------------------------------------------------
        # Get selected document
        # ----------------------------------------------------

        if available_files:

            file_data = collection.get(
                ids=[selected_file]
            )

            if (
                file_data
                and file_data.get("documents")
            ):

                full_text = file_data["documents"][0]

                # ------------------------------------------------
                # Select random section
                # ------------------------------------------------

                if len(full_text) > 4000:

                    start_idx = random.randint(
                        0,
                        len(full_text) - 4000
                    )

                else:

                    start_idx = 0

                sample_text = full_text[
                    start_idx:start_idx + 4000
                ]


        # ====================================================
        # PROMPT
        # ====================================================

        prompt = f"""

You are an expert Tamil government exam quiz creator.

Read ONLY the document text given below.

Create ONE high-quality multiple-choice question (MCQ).

IMPORTANT RULES:

1. Question MUST be in Tamil.
2. All four options MUST be in Tamil.
3. The question must be based ONLY on the provided document text.
4. Do NOT invent facts that are not present in the document.
5. Create exactly four options.
6. Only ONE option should be correct.
7. Make the other three options believable but incorrect.
8. Do not use LaTeX.
9. Do not use dollar signs.
10. Keep the question suitable for government competitive exams.
11. Do not provide the answer in this response.
12. Do not provide an explanation in this response.

Use EXACTLY this format:

Question: [தமிழில் கேள்வி]

a. [விருப்பம் A]

b. [விருப்பம் B]

c. [விருப்பம் C]

d. [விருப்பம் D]


DOCUMENT TEXT:

{sample_text}

"""


        # ====================================================
        # GEMINI API CALL
        # ====================================================

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )


        # ====================================================
        # SAVE RESULT
        # ====================================================

        if response and response.text:

            st.session_state.ai_question = response.text

            st.session_state.context_used = sample_text

            st.session_state.question_count += 1

            st.session_state.evaluation_result = ""

            st.session_state.detailed_explanation = ""

        else:

            st.error(
                "❌ Gemini எந்த கேள்வியையும் உருவாக்கவில்லை."
            )


    except Exception as e:

        st.error(
            f"❌ Error generating question:\n\n{e}"
        )


# ============================================================
# 7. START / NEXT QUESTION BUTTON
# ============================================================

st.markdown("---")

if st.button(
    "🚀 வினாடி வினாவைத் தொடங்குக / அடுத்த கேள்வி",
    use_container_width=True
):

    generate_new_question()


# ============================================================
# 8. DISPLAY QUESTION
# ============================================================

if st.session_state.ai_question:

    st.markdown(
        f"### 📊 வினா எண்: "
        f"{st.session_state.question_count}"
    )

    st.markdown(
        st.session_state.ai_question
    )


    # ========================================================
    # USER ANSWER
    # ========================================================

    user_choice = st.radio(
        "உங்கள் விடை விருப்பத்தைத் தேர்ந்தெடுக்கவும்:",
        ("a", "b", "c", "d"),
        key=f"q_{st.session_state.question_count}"
    )


    # ========================================================
    # SUBMIT BUTTON
    # ========================================================

    if st.button(
        "சமர்ப்பித்து மதிப்பிடுக ➡️",
        use_container_width=True
    ):

        with st.spinner(
            "🤖 AI உங்கள் பதிலைச் சரிபார்க்கிறது..."
        ):

            try:

                # ============================================
                # EVALUATION PROMPT
                # ============================================

                eval_prompt = f"""

You are an expert Tamil government exam evaluator.

Analyze the following question.

QUESTION AND OPTIONS:

{st.session_state.ai_question}


REFERENCE DOCUMENT:

{st.session_state.context_used}


USER SELECTED OPTION:

{user_choice}


TASK:

1. Identify the correct option.
2. Check the user's selected option.
3. Decide whether the user is correct or incorrect.
4. Respond completely in Tamil.
5. If the user is correct:
   Start with:
   ✅ **நன்று! (சரியான பதில்)**

   Then explain briefly why the answer is correct.

6. If the user is incorrect:
   Start with:
   ❌ **தவறு! (தவறான பதில்)**

   Then provide:
   - Correct option
   - Correct answer
   - Short explanation in Tamil

7. The explanation must be based ONLY on the reference document.
8. Do not invent information.

"""


                # ============================================
                # GEMINI EVALUATION
                # ============================================

                eval_response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=eval_prompt
                )


                # ============================================
                # SAVE EVALUATION
                # ============================================

                if (
                    eval_response
                    and eval_response.text
                ):

                    st.session_state.evaluation_result = (
                        eval_response.text
                    )

                else:

                    st.error(
                        "❌ AI மதிப்பீடு கிடைக்கவில்லை."
                    )


            except Exception as e:

                st.error(
                    f"❌ Error evaluating answer:\n\n{e}"
                )


    # ========================================================
    # 9. DISPLAY EVALUATION
    # ========================================================

    if st.session_state.evaluation_result:

        st.markdown("---")

        st.subheader(
            "📢 AI மதிப்பீடு:"
        )

        st.markdown(
            st.session_state.evaluation_result
        )
