import streamlit as st
import openai
import pdfplumber, docx
from io import StringIO

st.set_page_config(page_title="JD → Boolean Generator", layout="wide")
st.title("🔑 JD → Boolean Search-String Generator")

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ───────────────────────── helper to read JD file ────────────────────────────
def load_text(upload):
    if upload.name.endswith(".pdf"):
        with pdfplumber.open(upload) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])
    if upload.name.endswith(".docx"):
        return "\n".join([p.text for p in docx.Document(upload).paragraphs])
    return StringIO(upload.getvalue().decode()).read()

# ───────────────────────── prompt builder ─────────────────────────────────────
def build_prompt(jd, not_filters, user_ctx=""):
    instr = (
        "You are an HR sourcing assistant.\n"
        "1. Extract 4–6 *key skill buckets* from the job description.\n"
        "2. List 3–6 common synonyms/phrases for each bucket.\n"
        "3. IF USER CONTEXT is provided, treat it as a **hard filter**:\n"
        "   • Keep ONLY buckets aligned with that context.\n"
        "   • Discard JD skills that are not aligned.\n"
        "4. Build a Boolean search string: OR within a bucket, AND between buckets.\n"
        "5. Append NOT-filters.\n"
        "Return Markdown with two sections:\n"
        "### Buckets\n* Bucket – [syn1, syn2]\n### Boolean\n<string>\n"
    )
    if user_ctx:
        instr += f"\nUSER CONTEXT (strict): {user_ctx}\n"

    instr += f"\nNOT filters: {not_filters}\n\nJOB DESCRIPTION:\n{jd}"
    return instr

def gen_boolean(jd, not_filters, user_ctx=""):
    prompt = build_prompt(jd, not_filters, user_ctx)
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return resp.choices[0].message.content

# ────────────────────────────── UI ────────────────────────────────────────────
st.subheader("Step 1 • Job Description")
jd_file = st.file_uploader("Upload JD (TXT / PDF / DOCX)", type=["txt", "pdf", "docx"])
jd_text = load_text(jd_file) if jd_file else st.text_area("…or paste JD here", height=220)

st.subheader("Step 2 • NOT-filters")
not_filters = st.text_input("Exclude terms (comma-separated)", '"intern", "fresher"')

if st.button("Generate Initial Boolean") and jd_text:
    with st.spinner("Generating…"):
        initial_md = gen_boolean(jd_text, not_filters)
    st.markdown("## Initial Result")
    st.markdown(initial_md)
    st.session_state["jd_text"] = jd_text
    st.session_state["not_filters"] = not_filters
    st.session_state["initial_md"] = initial_md

# ─────────────────── refinement with strict user context ─────────────────────
if "initial_md" in st.session_state:
    st.divider()
    st.subheader("Step 3 • Refine with Extra Context (hard filter)")
    user_ctx = st.text_area(
        "Add clarifications / priorities (e.g. 'Hands-on RBAC and CI/CD, ignore certifications')",
        height=120,
    )
    if st.button("Refine Boolean") and user_ctx.strip():
        with st.spinner("Refining…"):
            refined_md = gen_boolean(
                st.session_state["jd_text"],
                st.session_state["not_filters"],
                user_ctx,
            )
        st.markdown("## Refined Result")
        st.markdown(refined_md)
