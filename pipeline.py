import google.generativeai as genai
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

def configure_gemini(api_key):
    """Configures the Gemini API with the provided API key."""
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True

def upload_to_gemini(path, mime_type=None):
    """Uploads the given file to Gemini.

    See https://ai.google.dev/gemini-api/docs/prompting_with_media
    """
    file = genai.upload_file(path, mime_type=mime_type)
    # print(f"Uploaded file '{file.display_name}' as: {file.uri}")
    return file

def wait_for_files_active(files):
    """Waits for the given files to be active.

    Some files uploaded to the Gemini API need to be processed before they can
    be used as prompt inputs. The status will be in the "processing" state
    until ready. This function polls the file status until it's "active".
    """
    # print("Waiting for file processing...")
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            # print(".", end="", flush=True)
            time.sleep(2)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")
    # print("...all files ready")
    # print()

def get_available_models():
    """Lists available models that support generateContent."""
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name)
        
        # Sort to prioritize gemini-1.5-pro and gemini-1.5-flash
        models.sort(key=lambda x: (
            0 if "gemini-1.5-pro" in x else
            1 if "gemini-1.5-flash" in x else
            2
        ))
        
        return models
    except Exception as e:
        return []

import cv2
import re
import base64

def time_str_to_seconds(time_str):
    """Converts MM:SS or HH:MM:SS to seconds."""
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return 0

def extract_frame_base64(video_path, seconds):
    """Extracts a frame at the given second and returns it as a base64 string."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    cap.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return None
    
    # Encode frame to JPEG
    # Resize to max width 400px to keep base64 string small enough for markdown rendering
    height, width = frame.shape[:2]
    max_width = 400
    if width > max_width:
        new_width = max_width
        new_height = int(height * (max_width / width))
        frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

    _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{jpg_as_text}"

def process_sop_content(text, video_path):
    """
    Parses the SOP text for timestamps, extracts frames, and embeds them.
    Also handles Mermaid diagrams if needed (though they are just text).
    """
    # Regex for [TIMESTAMP: MM:SS]
    # Timestamp format from prompt: [TIMESTAMP: MM:SS]
    pattern = re.compile(r'\[TIMESTAMP:\s*(\d{1,2}:\d{2})\]')
    
    def replace_match(match):
        time_str = match.group(1)
        seconds = time_str_to_seconds(time_str)
        # print(f"Extracting frame at {time_str} ({seconds}s)")
        
        image_data = extract_frame_base64(video_path, seconds)
        if image_data:
            # Revert to standard markdown, resizing will be handled by CSS in app.py
            return f"\n![Snapshot at {time_str}]({image_data})\n"
        return match.group(0) # input string returned if extraction fails

    return pattern.sub(replace_match, text)

def generate_sop(video_path, observation_text, model_name="models/gemini-1.5-pro", observation_image_path=None):
    """
    Generates an SOP from the provided video and observations.
    """
    
    # upload video
    video_file = upload_to_gemini(video_path, mime_type="video/mp4")

    # wait for processing
    wait_for_files_active([video_file])
    
    # upload image if exists
    image_file = None
    if observation_image_path:
        image_file = upload_to_gemini(observation_image_path, mime_type="image/jpeg") # basic assumption, can be improved
        wait_for_files_active([image_file])

    model = genai.GenerativeModel(
      model_name=model_name,
    )

    # Prompt Engineering
    prompt_parts = [
        "You are an expert technical writer and engineer with decades of experience in verifying and documenting maintenance procedures.",
        "Your task is to analyze the provided video content (visuals and audio) along with the technician's observations to create a comprehensive Standard Operating Procedure (SOP) and Maintenance/Diagnostics Documentation.",
        "The documentation should be clear, concise, and easy to follow for new technicians.",
        "Please extract tribal knowledge demonstrated or spoken in the video.",
        "**Visuals**: For every critical step where a specific visual action is performed (e.g., removing a specific part, checking a gauge), you MUST include a timestamp tag in the exact format `[TIMESTAMP: MM:SS]`. Place this tag immediately after the step description.",
        "**Diagrams**: At the end of the SOP, include a Mermaid.js flowchart (using ```mermaid ... ``` block) validating the troubleshooting logic or the process flow.",
        "Structure the output in Markdown with the following sections:",
        "1.  **Title & Objective**: Clear title and the goal of the procedure.",
        "2.  **Safety Warnings**: Critical safety precautions mentioned or observed (e.g., PPE, lock-out tag-out).",
        "3.  **Tools & Materials**: List of tools and parts seen or mentioned.",
        "4.  **Step-by-Step Instructions**: Chronological steps with detailed descriptions. REMEMBER to include `[TIMESTAMP: MM:SS]` for key visual steps.",
        "5.  **Troubleshooting/Diagnostics**: If the video covers diagnostics, detail the symptoms and the logic for the fix.",
        "6.  **Tribal Knowledge/Tips**: Specific expert tips or 'gotchas' mentioned by the technician that aren't in standard manuals.",
        "7.  **Process Flow**: A Mermaid diagram of the procedure.",
        "\nHere is the video of the procedure:",
        video_file,
    ]

    if observation_text:
        prompt_parts.append(f"\nTechnician's Observations:\n{observation_text}")
    
    if image_file:
         prompt_parts.append("\nAdditional Visual Context:")
         prompt_parts.append(image_file)

    prompt_parts.append("\nGenerate the SOP now.")

    response = model.generate_content(prompt_parts)
    
    # Post-process to add images
    # We use the local video path to extract frames
    final_markdown = process_sop_content(response.text, video_path)

    return final_markdown
