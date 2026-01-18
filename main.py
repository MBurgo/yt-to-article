import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="TMF Content Multiplier", layout="wide")

# --- AUTHENTICATION ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except FileNotFoundError:
    st.error("Secrets file not found. Please create a .streamlit/secrets.toml file.")
    st.stop()
except KeyError:
    st.error("OPENAI_API_KEY not found in secrets. Please add it.")
    st.stop()

# --- HELPER FUNCTIONS ---

def get_video_id(url):
    """Extracts the video ID from various YouTube URL formats."""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def get_transcript(video_id):
    """Fetches the transcript using the v1.0+ Instance Method."""
    try:
        # --- THE FIX FOR v1.0+ ---
        # We must instantiate the class first: '()'
        loader = YouTubeTranscriptApi() 
        
        # Now we call .list() on the instance (not .list_transcripts on the class)
        transcript_list = loader.list(video_id)
        
        # Try to find a manual English transcript (AU/UK/US), fallback to auto-generated
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'en-AU', 'en-GB', 'en-US'])
        except:
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'en-AU', 'en-GB', 'en-US'])
            except:
                return "Error: No English transcript found. (Video might be too new or have captions disabled)."
        
        # Fetch the actual text data
        transcript_data = transcript.fetch()
        
        # Combine into a single string
        full_text = " ".join([t['text'] for t in transcript_data])
        return full_text
        
    except Exception as e:
        # Fallback for older versions (Just in case)
        if "object has no attribute 'list'" in str(e):
             return "Critical Version Mismatch: Please ensure youtube-transcript-api is updated."
        return f"Error: {str(e)}"

def generate_article(transcript_text, api_key):
    """Sends transcript to LLM to rewrite as a TMF article."""
    client = OpenAI(api_key=api_key)
    
    # --- SYSTEM PROMPT ---
    system_prompt = """
    You are a senior financial editor for The Motley Fool Australia. 
    Your goal is to transform a video transcript into a high-quality, educational news article.

    TONE GUIDELINES:
    - **Educational & Analytical:** Summarize the analysis clearly.
    - **Humble but Confident:** Use "we" and "us".
    - **Long-term Mindset:** Focus on business fundamentals.
    - **Compliance Safe:** Use language like "investors might watch" rather than "you must buy."

    STRUCTURE:
    1. **Headline:** Compelling and news-focused.
    2. **The Lede:** A 2-3 sentence intro.
    3. **Key Points:** Short paragraphs or bullet points.
    4. **The Foolish View:** A concluding summary.
    5. **Transition:** A bridge to the email capture (e.g. "While this is a strong company...").

    Input Text:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript_text}
            ],
            temperature=0.7 
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI Error: {str(e)}"

# --- UI LAYOUT ---

st.title("🃏 TMF Video-to-Article Generator")
st.markdown("Turn a *Stock in Focus* video into a draft article in seconds.")

col1, col2 = st.columns([2, 1])

with col1:
    youtube_url = st.text_input("Paste YouTube URL here:", placeholder="https://www.youtube.com/watch?v=...")
    generate_btn = st.button("Generate Article 🚀", type="primary")

if generate_btn:
    if not youtube_url:
        st.warning("Please paste a URL first.")
    else:
        video_id = get_video_id(youtube_url)
        if not video_id:
            st.error("Could not extract Video ID.")
        else:
            with st.spinner("🎧 Listening to video..."):
                transcript = get_transcript(video_id)
            
            if "Error:" in transcript:
                st.error(transcript)
            else:
                with st.spinner("✍️ Writing draft..."):
                    article_draft = generate_article(transcript, api_key)
                
                st.success("Draft ready!")
                st.markdown("---")
                st.subheader("📝 Your Article Draft")
                st.markdown(article_draft)
                st.download_button("Download Markdown", article_draft, file_name="article_draft.md")
