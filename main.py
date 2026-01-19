import streamlit as st
from openai import OpenAI

# --- CONFIGURATION ---
st.set_page_config(page_title="Foolish Video to Foolish Article Tool", layout="wide")

# --- AUTHENTICATION ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except FileNotFoundError:
    st.error("Secrets file not found. Please create a .streamlit/secrets.toml file.")
    st.stop()
except KeyError:
    st.error("OPENAI_API_KEY not found in secrets. Please add it.")
    st.stop()

# --- THE WRITER FUNCTION ---
def generate_article(raw_text, api_key):
    client = OpenAI(api_key=api_key)
    
    system_prompt = """
    You are a senior financial editor for The Motley Fool Australia. 
    Your goal is to transform a video transcript (or raw notes) into a high-quality, educational news article.

    TONE GUIDELINES:
    - **Educational & Analytical:** Summarize the analysis clearly.
    - **Humble but Confident:** Use "we" and "us" to represent the Fool team.
    - **Long-term Mindset:** Focus on business fundamentals, not just daily price moves.
    - **Compliance Safe:** Use language like "investors might watch" rather than "you must buy." 
    - **Formatting:** Use clear H2 headings and bullet points.

    STRUCTURE:
    1. **Headline:** Compelling, news-focused, and "Foolish" (e.g., "Why CSL Shares Are Moving Today").
    2. **The Lede:** A 2-3 sentence intro summarizing the main topic.
    3. **Key Points / The Analysis:** Extract the core arguments from the text.
    4. **The Foolish View:** A concluding paragraph that summarizes the long-term implication.
    5. **Transition:** A final sentence that seamlessly leads to an email capture (e.g., "While this is a strong company, there are other opportunities we are watching...").

    Input Text:
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.7 
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI Error: {str(e)}"

# --- UI LAYOUT ---

st.title("🃏 Foolish Videos --> Foolish Article Tool")
st.markdown("""
**How to use:**
1. Go to the YouTube video.
2. Click **More (... )** -> **Show Transcript**.
3. Click **Toggle Timestamps** (to hide them) and copy the text.
4. Paste below.
""")

col1, col2 = st.columns([2, 1])

with col1:
    # Changed from 'text_input' (single line) to 'text_area' (big box)
    raw_text = st.text_area("Paste Transcript / Notes here:", height=300)
    generate_btn = st.button("Generate Article 🚀", type="primary")

with col2:
    st.info("💡 **Tip:** You can also paste messy notes or a press release here. The AI will clean it up into the TMF style regardless of the input format.")

if generate_btn:
    if not raw_text:
        st.warning("Please paste some text first.")
    else:
        with st.spinner("✍️ Consulting the Foolish oracle..."):
            article_draft = generate_article(raw_text, api_key)
            
            if "Error" in article_draft:
                st.error(article_draft)
            else:
                st.success("Draft ready!")
                st.markdown("---")
                st.subheader("📝 Your Article Draft")
                st.markdown(article_draft)
                st.download_button("Download Markdown", article_draft, file_name="article_draft.md")
