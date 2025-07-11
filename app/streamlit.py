import streamlit as st
import requests
import json
from datetime import datetime
import time

# Page configuration
st.set_page_config(
    page_title="Islamic Chatbot",
    page_icon="🕌",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional styling
st.markdown("""
<style>
    .main {
        padding-top: 2rem;
    }
    
    .chat-container {
        max-height: 60vh;
        overflow-y: auto;
        padding: 1rem;
        border: 1px solid #e6e6e6;
        border-radius: 10px;
        background-color: #fafafa;
        margin-bottom: 1rem;
    }
    
    .user-message {
        display: flex;
        justify-content: flex-end;
        margin: 10px 0;
    }
    
    .bot-message {
        display: flex;
        justify-content: flex-start;
        margin: 10px 0;
    }
    
    .message-content {
        max-width: 70%;
        padding: 12px 16px;
        border-radius: 18px;
        word-wrap: break-word;
    }
    
    .user-content {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-bottom-right-radius: 5px;
    }
    
    .bot-content {
        background: white;
        color: #333;
        border: 1px solid #e6e6e6;
        border-bottom-left-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .message-icon {
        width: 35px;
        height: 35px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 10px;
        font-size: 18px;
    }
    
    .user-icon {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    .bot-icon {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
    }
    
    .header-container {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .input-container {
        position: sticky;
        bottom: 0;
        background: white;
        padding: 1rem 0;
        border-top: 1px solid #e6e6e6;
    }
    
    .arabic-text {
        font-family: 'Amiri', 'Times New Roman', serif;
        font-size: 1.2em;
        text-align: right;
        direction: rtl;
        line-height: 1.8;
        color: #2c5530;
        background: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #4CAF50;
        margin: 10px 0;
    }
    
    .reference-text {
        background: #e8f4f8;
        padding: 8px 12px;
        border-radius: 5px;
        border-left: 3px solid #2196F3;
        margin: 10px 0;
        font-weight: 500;
    }
    
    .stTextInput > div > div > input {
        border-radius: 25px;
        border: 2px solid #e6e6e6;
        padding: 12px 20px;
    }
    
    .stButton > button {
        border-radius: 25px;
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        border: none;
        color: white;
        font-weight: 600;
        padding: 12px 30px;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    
    .typing-indicator {
        display: flex;
        align-items: center;
        padding: 10px;
    }
    
    .typing-dots {
        display: flex;
        gap: 4px;
    }
    
    .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #667eea;
        animation: typing 1.4s infinite ease-in-out;
    }
    
    .dot:nth-child(1) { animation-delay: -0.32s; }
    .dot:nth-child(2) { animation-delay: -0.16s; }
    
    @keyframes typing {
        0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
        40% { transform: scale(1); opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

def send_query(query):
    """Send query to FastAPI backend"""
    try:
        response = requests.post(
            "http://127.0.0.1:8000/query",
            json={"query": query},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"Error: {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Connection error: {str(e)}"

# Main UI
def main():
    # Header
    st.markdown("""
    <div class="header-container">
        <h1>🕌 Islamic Knowledge Chatbot</h1>
        <p>Ask questions about Islamic teachings, Quran verses, and Islamic guidance</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Simple input and response
    st.markdown("### Ask your question:")
    user_input = st.text_input("Question:", placeholder="Type your Islamic question here...")
    
    if st.button("Send", type="primary"):
        if user_input.strip():
            with st.spinner("Getting response..."):
                bot_response = send_query(user_input)
            
            st.markdown("#### Your Question:")
            st.write(user_input)
            
            st.markdown("#### Response:")
            st.markdown(bot_response)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### About")
        st.info("This chatbot provides Islamic knowledge based on authentic sources.")
        
        st.markdown("### Features")
        st.markdown("""
        - 📖 Quranic verses with Arabic text
        - 🔍 Authentic Islamic teachings
        - 📚 Sourced references
        """)

if __name__ == "__main__":
    main()