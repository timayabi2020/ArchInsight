import streamlit as st
import fitz  # PyMuPDF
from PIL import Image, ImageEnhance
import io
import os
from dotenv import load_dotenv

from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains.summarize import load_summarize_chain
from langchain.docstore.document import Document

# Page config
st.set_page_config(page_title="ArchInsight", layout="wide")
st.title("📐 ArchInsight – Architectural Diagram Summarizer")

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize LLM
llm = ChatOpenAI(
    temperature=0.2,
    openai_api_key=OPENAI_API_KEY,
    model_name="gpt-3.5-turbo"
)

# Keywords to filter pages likely containing diagrams
diagram_keywords = ["architecture"]

def extract_diagram_pages(pdf_file):
    text_blocks = []
    images = []

    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for i, page in enumerate(doc):
            text = page.get_text()
            text_blocks.append((i, text))

            if any(kw in text.lower() for kw in diagram_keywords):
                pix = page.get_pixmap(dpi=200)
                image_bytes = pix.tobytes("png")
                images.append({
                    "page": i,
                    "image": image_bytes,
                    "caption": f"Diagram Page {i + 1}"
                })

    return text_blocks, images

def summarize_diagram_context(context_text):
    docs = [Document(page_content=context_text)]
    prompt_template = PromptTemplate.from_template("""
You are a senior systems architect assistant.

Given the following text surrounding a **technical architecture diagram**, generate a **detailed and specific** summary that includes:

1. **What the diagram represents** — e.g. CI/CD pipeline, infrastructure, or component-level design.
2. **Key systems, machines, services, and workflows** shown in the diagram — name them concretely.
3. **How data or jobs flow** between these parts (e.g., from git to build system to testbed).
4. **Why the diagram matters** in the broader technical context — e.g. deployment automation, testing, integration, or network simulation.

Be clear and concise, but avoid generic descriptions.
Use bullet points if needed.

Context:
{page_content}
""")
    chain = load_summarize_chain(llm, chain_type="stuff", prompt=prompt_template, document_variable_name="page_content")
    result = chain.run(docs)
    return result

uploaded_file = st.file_uploader("Upload a PDF document", type="pdf")

if uploaded_file:
    text_blocks, images = extract_diagram_pages(uploaded_file)

    if images:
        st.success(f"Found {len(images)} page(s) likely containing architectural diagrams.")
    else:
        st.warning("No diagram-like pages detected based on keywords.")

    for img_data in images:
        page = img_data["page"]
        caption = img_data["caption"]
        image = Image.open(io.BytesIO(img_data["image"]))

        # Optional: enhance contrast for better line visibility
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(1.5)  # You can tweak between 1.2 - 2.0

        st.image(enhanced, caption=caption, use_container_width=True)

        context_text = text_blocks[page][1]
        with st.spinner(f"Summarizing context for {caption}..."):
            summary = summarize_diagram_context(context_text)

        st.subheader("📝 Summary")
        st.write(summary)
        st.markdown("---")
