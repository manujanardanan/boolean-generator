import streamlit as st
import openai
import pdfplumber, docx
from io import StringIO

st.set_page_config(page_title="JD → Boolean Generator", layout="wide")
st.title("🔑 JD → Boolean Search-String Generator")

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ──────────────────────────── helpers ────────────────────────────
def load_text(upload):
    if upload.name.endswith(".pdf"):
        with pdfplumber.open(upload) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    if upload.name.endswith(".docx"):
        return "\n".join([p.text for p in docx.Document(upload).paragraphs])
    return StringIO(upload.getvalue().decode()).read()

def boolean_prompt(jd, not_filters, user_context=""):
    base = (
        "You are an HR-sourcing assistant.\n"
        "1. Extract 4-6 key skill buckets from the job description.\n"
        "2. For each bucket list common synonyms / phrases (3-6 each).\n"
        "3. If USER CONTEXT is provided, use it to prioritise MUST-HAVES vs nice-to-haves "
        "and drop irrelevant skills.\n"
        "4. Build a Boolean search string:\n"
        "   - OR within a bucket, AND between buckets.\n"
        "   - Append NOT-filters.\n"
        "Return Markdown with two sections:\n"
        "### Buckets\n* Bucket – [syn1, syn2]\n### Boolean\n<string>\n"
    )
    if user_context:
        base += f"\nUSER CONTEXT: {user_context}\n"
    base += f"\nNOT filters: {not_filters}\n\nJOB DESCRIPTION:\n{jd}"
    return base

def generate_boolean(jd, not_filters, user_context=""):
    prompt = boolean_prompt(jd, not_filters, user_context)
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return resp.choices[0].message.content
# ──────────────────────────── UI ─────────────────────────────────
st.subheader("Step 1 • Job Description")
jd_file = st.file_uploader("Upload JD (TXT / PDF / DOCX)", type=["txt", "pdf", "docx"])
jd_text = load_text(jd_file) if jd_file else st.text_area("…or paste JD here", height=220)

st.subheader("Step 2 • Optional NOT-filters")
not_filters = st.text_input("Exclude these terms (comma-separated)", '"intern", "fresher"')

if st.button("Generate Initial Boolean") and jd_text:
    with st.spinner("Generating…"):
        initial_md = generate_boolean(jd_text, not_filters)
    st.markdown("## Initial Result")
    st.markdown(initial_md)
    st.session_state["initial_md"] = initial_md  # store for display

# ─────────────────────── user-context refinement ─────────────────
if "initial_md" in st.session_state:
    st.divider()
    st.subheader("Step 3 • Refine with Extra Context")
    context_help = "E.g. 'Hands-on RBAC, less focus on certifications', 'Prefer multi-subscription Azure experience'."
    user_context = st.text_area("Add clarifications / priorities", placeholder=context_help, height=120)
    if st.button("Refine Boolean") and user_context.strip():
        with st.spinner("Refining…"):
            refined_md = generate_boolean(jd_text, not_filters, user_context)
        st.markdown("## Refined Result")
        st.markdown(refined_md)
