
# AI Maintenance SOP Generator 🛠️

This application processes egocentric maintenance videos to automatically generate Standard Operating Procedures (SOPs). It leverages Google's Gemini 1.5 Pro AI model to extract tribal knowledge, create step-by-step instructions, and identify safety warnings.

## Features

- **Video Upload**: Supports MP4, MOV, AVI, etc.
- **AI Analysis**: Uses Gemini 1.5 Pro for deep video understanding.
- **Visuals**: Automatically extracts relevant frames and generates Mermaid diagrams.
- **PDF Export**: Download the generated SOP as a professional PDF.
- **Customizable**: User can provide specific observations and context.

## Setup

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set up your Google API Key in `.env` or via the sidebar in the app.
4.  Run the app:
    ```bash
    streamlit run app.py
    ```

## Deployment

This app is ready for deployment on [Streamlit Community Cloud](https://streamlit.io/cloud).
