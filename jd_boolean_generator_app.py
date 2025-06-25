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
    """
    Build a system prompt that…
    1. Uses user_ctx as the ONLY source of MUST-HAVE skills.
    2. Lets the JD supply synonyms/examples, but never introduce new buckets.
    3. Forces “resume language” synonyms (e.g., GL, cost-center for Finance Master Data).
    """
    instructions = (
        "You are an HR sourcing assistant.\n"
        "● Step-A  (Prioritize)\n"
        "  Read the USER CONTEXT below and extract 3-5 MUST-HAVE skill buckets—nothing else.\n"
        "● Step-B  (Resume Language)\n"
        "  For each bucket, list 5-10 ways that skill is **likely written on real resumes** "
        "(abbreviations, module names, domain jargon, project phrases). "
        "Ignore buzz-words copied verbatim from the JD if they’re seldom on resumes.\n"
        "● Step-C  (Boolean)\n"
        "  Build a Boolean search string:\n"
        "    • OR within a bucket (use resume-style synonyms).\n"
        "    • AND between buckets.\n"
        "    • Append the NOT-filters.\n"
        "● Output Markdown in exactly this template:\n"
        "### Buckets\n"
        "* <Bucket-1> – [syn1, syn2, …]\n"
        "* <Bucket-2> – […]\n"
        "### Boolean\n"
        "<boolean string>\n"
    )

    if user_ctx:
        instructions += f"\nUSER CONTEXT (must-haves, strict):\n{user_ctx}\n"
    instructions += f"\nNOT filters: {not_filters}\n"
    instructions += f"\n---\nJob Description (only for extra synonyms, NOT for new buckets):\n{jd}"

    return instructions
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
