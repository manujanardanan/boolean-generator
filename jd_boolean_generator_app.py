import streamlit as st
import openai
import pdfplumber, docx
from io import StringIO

# ─────────────────────────  Streamlit setup  ─────────────────────────
st.set_page_config(page_title="JD → Boolean Generator", layout="wide")
st.title("🔑 JD → Boolean Search-String Generator")

client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ───────────────────────────── helpers ───────────────────────────────
def load_text(upload):
    """Read TXT, PDF, or DOCX into plain text."""
    if upload.name.lower().endswith(".pdf"):
        with pdfplumber.open(upload) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    if upload.name.lower().endswith(".docx"):
        return "\n".join(p.text for p in docx.Document(upload).paragraphs)
    return StringIO(upload.getvalue().decode()).read()

def build_prompt(jd, not_filters, user_ctx=""):
    """
    Prompt: only user_ctx defines MUST-HAVE buckets.
    JD is used solely for resume-style synonyms.
    """
    instructions = (
        "You are an HR sourcing assistant.\n"
        "1. Extract 3-5 MUST-HAVE skill buckets strictly from USER CONTEXT.\n"
        "2. For each bucket, list 4-8 synonyms or phrases as they appear on real resumes "
        "(module names, abbreviations, domain jargon). DO NOT invent new buckets from the JD.\n"
        "3. Build a Boolean search string: OR within buckets, AND between buckets; "
        "append NOT-filters.\n"
        "Return Markdown in exactly this template:\n"
        "### Buckets\n"
        "* <Bucket-1> – [syn1, syn2, …]\n"
        "* <Bucket-2> – …\n"
        "### Boolean\n"
        "<boolean string>\n"
    )
    if user_ctx:
        instructions += f"\nUSER CONTEXT (strict):\n{user_ctx}\n"
    instructions += f"\nNOT filters: {not_filters}\n"
    instructions += (
        "\n---\nJob Description (use only for additional synonyms, "
        "do NOT create new buckets):\n" + jd
    )
    return instructions

def gen_boolean(jd, not_filters, user_ctx=""):
    prompt = build_prompt(jd, not_filters, user_ctx)
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return resp.choices[0].message.content

# ────────────────────────────── UI ───────────────────────────────────
st.subheader("Step 1 • Job Description")
jd_file = st.file_uploader("Upload JD (TXT / PDF / DOCX)", type=["txt", "pdf", "docx"])
jd_text = load_text(jd_file) if jd_file else st.text_area("…or paste JD here", height=220)

st.subheader("Step 2 • NOT filters")
not_filters = st.text_input("Exclude terms (comma-separated)", '"intern", "fresher"')

# Initial generation
if st.button("Generate Initial Boolean") and jd_text:
    with st.spinner("Generating…"):
        initial_md = gen_boolean(jd_text, not_filters)   # ← defined above
    st.markdown("## Initial Result")
    st.markdown(initial_md)
    # store for refinement
    st.session_state.jd_text = jd_text
    st.session_state.not_filters = not_filters

# Refinement block
if "jd_text" in st.session_state:
    st.divider()
    st.subheader("Step 3 • Refine with Extra Context (hard filter)")
    user_ctx = st.text_area(
        "Add clarifications / priorities (e.g. 'Hands-on RBAC, CI/CD; ignore certifications')",
        height=120,
    )
    if st.button("Refine Boolean") and user_ctx.strip():
        with st.spinner("Refining…"):
            refined_md = gen_boolean(
                st.session_state.jd_text,
                st.session_state.not_filters,
                user_ctx,
            )
        st.markdown("## Refined Result")
        st.markdown(refined_md)
