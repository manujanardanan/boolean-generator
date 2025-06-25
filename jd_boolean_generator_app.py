import streamlit as st
import openai
import pdfplumber, docx
from io import StringIO

st.set_page_config(page_title="JD → Boolean Generator", layout="wide")
st.title("🔑 JD → Boolean Search-String Generator")

# ───────────────────────────────────  OpenAI  ──────────────────────────────────
client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ───────────────────────────  Helper: read JD file  ───────────────────────────
def load_text(upload):
    if upload.name.endswith(".pdf"):
        with pdfplumber.open(upload) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    elif upload.name.endswith(".docx"):
        return "\n".join([p.text for p in docx.Document(upload).paragraphs])
    else:                       # .txt
        return StringIO(upload.getvalue().decode()).read()

# ──────────────────────────────  UI  ──────────────────────────────────────────
st.subheader("Step 1  •  Job Description")
jd_file = st.file_uploader("Upload JD (TXT / PDF / DOCX)", type=["txt", "pdf", "docx"])
jd_text = load_text(jd_file) if jd_file else st.text_area("…or paste JD here", height=220)

st.subheader("Step 2  •  Optional NOT-filters")
default_nots = '"intern", "fresher", "trainee"'
not_filters = st.text_input("Comma-separated terms to EXCLUDE", value=default_nots)

if st.button("Generate Boolean String") and jd_text:
    with st.spinner("Crafting Boolean search…"):
        prompt = (
            "You are an HR sourcing assistant. "
            "1. Read the job description and extract 4-6 key skill groups. "
            "2. For each group, list common synonyms or alternate phrasings. "
            "3. Produce a Boolean search string for LinkedIn/Naukri: "
            "   - Use OR within a group, AND between groups. "
            "   - Incorporate the NOT-filters provided. "
            "4. Show output in Markdown:\n"
            "   ### Skill Buckets\n"
            "   * Bucket → [synonyms]\n"
            "   ### Boolean String\n"
            f"NOT-filters: {not_filters}\n\n"
            f"Job Description:\n{jd_text}"
        )
        answer = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        ).choices[0].message.content

    st.markdown(answer)
else:
    st.info("Upload or paste the JD, then click **Generate Boolean String**.")

