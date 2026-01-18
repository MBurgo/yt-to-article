import streamlit as st
import sys
import subprocess
import importlib
import re
from openai import OpenAI

# --- PAGE CONFIG ---
st.set_page_config(page_title="TMF Content Multiplier", layout="wide")

# --- SELF-HEALING DEPENDENCY CHECK ---
# This block runs before the app loads to ensure the library is not broken.
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    # Test if the modern method exists
    getattr(YouTubeTranscriptApi, 'list_transcripts')
except (ImportError, AttributeError):
    st.warning("🛠️ Detected outdated 'youtube-transcript-api'. Auto-repairing... please wait 10 seconds.")
    try:
        # Force upgrade the package
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "youtube-transcript-api"])
        st.success("✅ Repair complete! Please refresh your browser page now.")
        st.stop()
    except Exception as e:
        st.error(f"Auto-repair failed: {e}. Please run `pip install --upgrade youtube-transcript-api` in your terminal.")
        st.stop()

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
    """Fetches the transcript using the new API method."""
    try:
        # 1. Fetch the list of available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 2. Try to find a manual English transcript (AU/UK/US), fallback to auto-generated
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'en-AU', 'en-GB', 'en-US'])
        except:
            try:
                transcript = transcript_list.find_generated_transcript(['en', 'en-AU', 'en-GB', 'en-US'])
            except:
                return "Error: No English transcript found for this video."
        
        # 3. Fetch the actual text data
        transcript_data = transcript.fetch()
        
        # 4. Combine into a single string
        full_text = " ".join([t['text'] for t in transcript_data])
        return full_text
        
    except Exception as e:
        return f"Error: {str(e)}"

def generate_article(transcript_text, api_key):
    """Sends transcript to LLM to rewrite as a TMF article."""
    client = OpenAI(api_key=api_key)
    
    # --- SYSTEM PROMPT (EDUCATIONAL FOCUS) ---
    system_prompt = """
    You are a senior financial editor for The Motley Fool Australia. 
    Your goal is to transform a video transcript into a high-quality, educational news article.

    TONE GUIDELINES:
    - **Educational & Analytical:** The video is likely analyzing a stock or market news. Your job is to summarize this analysis clearly.
    - **Humble but Confident:** Use "we" and "us" to represent the Fool team.
    - **Long-term Mindset:** Focus on the business fundamentals discussed, not just daily price moves.
    - **Compliance Safe:** Use language like "investors might watch" or "the company reported," rather than "you must buy this."

    STRUCTURE:
    1. **Headline:** Compelling and news-focused (e.g., "Why CSL Shares Are Moving Today").
    2. **The Lede:** A 2-3 sentence intro summarizing the main topic or news event.
    3. **Key Points:** Use short paragraphs or bullet points to explain the analysis provided in the video.
    4. **The Foolish View:** A concluding paragraph that summarizes the long-term implication for investors.
    5. **Transition:** A final sentence that naturally leads the reader to want more information (e.g., "While this is a strong company, there are other opportunities we are watching..."). This serves as a bridge to our email capture form.

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

# Main Input Area
col1, col2 = st.columns([2, 1])

with col1:
    youtube_url = st.text_input("Paste YouTube URL here:", placeholder="https://www.youtube.com/watch?v=...")
    generate_btn = st.button("Generate Article 🚀", type="primary")

# Processing Logic
if generate_btn:
    if not youtube_url:
        st.warning("Please paste a URL first.")
    else:
        video_id = get_video_id(youtube_url)
        
        if not video_id:
            st.error("Could not extract Video ID. Check the URL format.")
        else:
            with st.spinner("🎧 Listening to video (fetching transcript)..."):
                transcript = get_transcript(video_id)
            
            if "Error:" in transcript:
                st.error(transcript)
            else:
                with st.spinner("✍️ Writing draft (consulting the Foolish oracle)..."):
                    article_draft = generate_article(transcript, api_key)
                
                st.success("Draft ready!")
                st.markdown("---")
                st.subheader("📝 Your Article Draft")
                st.markdown(article_draft)
                st.download_button("Download Markdown", article_draft, file_name="article_draft.md")
                
                with st.expander("View Original Transcript"):
                    st.text(transcript)
