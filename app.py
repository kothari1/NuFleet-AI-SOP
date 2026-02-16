import streamlit as st
import tempfile
import os
from pipeline import configure_gemini, generate_sop
from dotenv import load_dotenv
from fpdf import FPDF

# Load environment variables
load_dotenv()

st.set_page_config(page_title="AI Maintenance SOP Generator", page_icon="🛠️", layout="wide")

st.title("🛠️ AI Maintenance SOP Generator")
st.markdown("Upload egocentric videos of technical procedures to automatically generate comprehensive Standard Operating Procedures (SOPs) using Gemini 1.5 Pro.")

# Custom CSS to limit image size in SOP (Optional now that images are resized at source)
st.markdown("""
<style>
    .stMarkdown img {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar for Configuration
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Google AI API Key", type="password", help="Enter your Google AI Studio API Key. If you have a .env file, it will be loaded automatically.")

# Check if API Key is available from env or input
if not api_key:
    api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.warning("⚠️ Please enter your Google AI API Key in the sidebar to proceed.")
    st.stop()

if not configure_gemini(api_key):
    st.error("❌ Failed to configure Gemini API. Please check your API Key.")
    st.stop()

st.sidebar.success("✅ API Key Configured")

from pipeline import get_available_models
available_models = get_available_models()

# Default to gemini-1.5-pro or gemini-1.5-flash
default_index = 0
for i, m in enumerate(available_models):
    if "gemini-1.5-pro" in m and "latest" in m: # prefer latest 1.5 pro
        default_index = i
        break
    elif "gemini-1.5-pro" in m:
        default_index = i
        break # stop at first 1.5 pro if no 'latest' found yet

selected_model = st.sidebar.selectbox("Select Model", available_models, index=default_index if available_models else 0)
if not selected_model:
    st.sidebar.warning("No models found. Check API key permissions.")
    selected_model = "models/gemini-1.5-pro" # Fallback manual entry

st.sidebar.info("💡 **Tip**: Use `gemini-1.5-pro` or `gemini-1.5-flash` for best results with long videos.")

# Main Content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("1. Upload Media")
    uploaded_video = st.file_uploader("Upload Maintenance Video", type=["mp4", "mov", "avi", "mkv"])
    
    if uploaded_video:
        st.video(uploaded_video)
        
    st.header("2. Technician Observations")
    observation_text = st.text_area("Add specific notes, warnings, or context (Tribal Knowledge)", height=150, placeholder="e.g., 'Be careful with the plastic clip, it breaks easily if pulled too hard.'")
    
    uploaded_image = st.file_uploader("Upload Additional Image (Optional)", type=["jpg", "jpeg", "png"])
    if uploaded_image:
        st.image(uploaded_image, caption="Observation Image", use_column_width=True)

with col2:
    st.header("3. Generate Documentation")
    
    if uploaded_video:
        if st.button("Generate SOP 🚀", type="primary"):
            with st.spinner("Analyzing video and generating SOP... This may take a minute depending on video length."):
                try:
                    # Save uploaded files to temp files
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
                        tmp_video.write(uploaded_video.read())
                        video_path = tmp_video.name
                    
                    image_path = None
                    if uploaded_image:
                         with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_image:
                            tmp_image.write(uploaded_image.read())
                            image_path = tmp_image.name

                    # Generate SOP
                    sop_content = generate_sop(video_path, observation_text, selected_model, image_path)
                    
                    st.success("✅ SOP Generated Successfully!")
                    st.session_state['generated_sop'] = sop_content
                    
                    # Cleanup temp files
                    os.remove(video_path)
                    if image_path:
                        os.remove(image_path)
                        
                except Exception as e:
                    st.error(f"Error generating SOP: {str(e)}")
    else:
        st.info("👈 Please upload a video to start.")

# Display Generated SOP
if 'generated_sop' in st.session_state:
    st.divider()
    st.header("📄 Generated SOP")
    
    # Split content to find mermaid blocks for custom rendering
    content = st.session_state['generated_sop']
    
    # Simple check for mermaid block
    if "```mermaid" in content:
        parts = content.split("```mermaid")
        for i, part in enumerate(parts):
            if i % 2 == 0:
                st.markdown(part)
            else:
                # The mermaid code is in this part, up to the next ```
                mermaid_code = part.split("```")[0]
                rest = part.split("```")[1] if len(part.split("```")) > 1 else ""
                
                st.caption("Process Flow Diagram")
                try:
                    import streamlit_mermaid as st_mermaid
                    st_mermaid.st_mermaid(mermaid_code, height=400)
                except ImportError:
                    st.code(mermaid_code, language="mermaid")
                    st.info("Install `streamlit-mermaid` to render this diagram visually.")
                
                st.markdown(rest, unsafe_allow_html=True)
    else:
        st.markdown(content, unsafe_allow_html=True)
    
    # PDF Export
    st.subheader("Export")
    if st.button("Generate PDF"):
        with st.spinner("Generating PDF..."):
            
            # Simple PDF Class with HTML support
            class PDF(FPDF):
                def header(self):
                    self.set_font('helvetica', 'B', 15)
                    self.cell(0, 10, 'Maintenance SOP', align='C', new_x="LMARGIN", new_y="NEXT")
                    self.ln(10)
            
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("helvetica", size=12)
            
            # Custom Markdown to HTML converter for FPDF
            # FPDF2 HTMLMixin supports: <b>, <i>, <u>, <a>, <br>, <p>, <font>, <h1>...<h6>, <ul>, <ol>, <li>, <img>, <table>
            import re
            
            def specific_markdown_to_html(text):
                html = text
                # Bold
                html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
                # Italic
                html = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html)
                
                # Headers
                html = re.sub(r'^#\s+(.*)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
                html = re.sub(r'^##\s+(.*)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
                html = re.sub(r'^###\s+(.*)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
                
                # Lists - simplistic approach
                # Unordered
                html = re.sub(r'(?m)^-\s+(.*)$', r'<li>\1</li>', html)
                # Wrap consecutive li in ul (basic attempt, FPDF is forgiving)
                # Actually FPDF might just take <li> and treat it well enough or we need <ul>
                # Let's just wrap lines with - in <ul> manually if needed, but for now <li> might usually render ok-ish or we can prefix
                
                # Numbered lists
                html = re.sub(r'(?m)^\d+\.\s+(.*)$', r'<li>\1</li>', html)
                
                # Images - convert standard markdown img to HTML img
                # ![Alt](src) -> <img src="src" width="WIDTH">
                # We need to ensure src is local path or data uri
                html = re.sub(r'!\[.*?\]\((.*?)\)', r'<img src="\1" width="300">', html)
                
                # Line breaks to <br>
                html = html.replace('\n', '<br>')
                
                return html

            html_content = specific_markdown_to_html(content)
            
            try:
                pdf.write_html(html_content)
                pdf_output = pdf.output() # Returns bytes
                
                st.success("✅ PDF Generated!")
                st.download_button(
                    label="Download PDF",
                    data=bytes(pdf_output),
                    file_name="maintenance_sop.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Error generating PDF: {str(e)}")
                # st.write(html_content) # debug
    
    # st.download_button(
    #     label="Download SOP as Markdown",
    #     data=st.session_state['generated_sop'],
    #     file_name="maintenance_sop.md",
    #     mime="text/markdown"
    # )
