import streamlit as st
import anthropic
import os
import copy
import base64
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Set up Streamlit UI
st.set_page_config(page_title="Claude Chatbot", layout="wide")
st.title("Chat with Claude AI")

# Load Firebase credentials (store in Streamlit secrets)
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_CREDENTIALS"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Function to start a new chat session
def start_new_chat():
    new_chat_name = f"Chat {len(st.session_state.chat_sessions) + 1}"
    st.session_state.chat_sessions[new_chat_name] = {"messages": []}  # Store in Firestore
    st.session_state.current_chat = new_chat_name
    st.session_state.messages = []
    st.session_state.uploaded_file = None  # Reset file input
    save_chat_sessions()

# Save chat sessions to Firestore
def save_chat_sessions():
    for session_name, data in st.session_state.chat_sessions.items():
        db.collection("chat_sessions").document(session_name).set({"messages": data["messages"]})

# Load chat sessions from Firestore
def load_chat_sessions():
    docs = db.collection("chat_sessions").stream()
    st.session_state.chat_sessions = {doc.id: {"messages": doc.to_dict().get("messages", [])} for doc in docs}
    
    # If Firestore is empty, create a default chat session
    if not st.session_state.chat_sessions:
        start_new_chat()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}
    load_chat_sessions()
if "current_chat" not in st.session_state:
    st.session_state.current_chat = None
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# Sidebar settings
st.sidebar.header("Settings")
uploaded_file = st.sidebar.file_uploader("Attach a file", type=["pdf", "jpeg", "png", "webp"], label_visibility="collapsed")
max_tokens = st.sidebar.slider("Max Tokens", min_value=1024, max_value=128000, value=1700)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
thinking_mode = st.sidebar.toggle("Thinking Mode", value=True)
thinking_token_budget = st.sidebar.slider("Thinking Token Budget", min_value=1024, max_value=128000, value=1048)

st.sidebar.header("Chat History")
st.sidebar.button("New Chat", on_click=start_new_chat)

# Ensure there is at least one chat session
if not st.session_state.chat_sessions:
    start_new_chat()

# Display chat sessions in reversed order (latest at top)
chat_keys = list(st.session_state.chat_sessions.keys())[::-1]

# Prevent errors if no chat exists
if not chat_keys:
    selected_chat = None
    st.sidebar.write("No chat history found. Start a new chat.")
else:
    selected_chat = st.sidebar.radio(
        "Chat Sessions", 
        chat_keys, 
        index=chat_keys.index(st.session_state.current_chat) if st.session_state.current_chat in chat_keys else 0
    )

if selected_chat and selected_chat != st.session_state.current_chat:
    st.session_state.current_chat = selected_chat
    st.session_state.messages = st.session_state.chat_sessions[selected_chat]["messages"][:]
    st.session_state.uploaded_file = None  # Reset file input when switching chats
    st.rerun()

# Load API key from Streamlit secrets
api_key_claude = st.secrets["ANTHROPIC_API_KEY"]

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=api_key_claude,
)

# Display chat history with alignment styles
for message in st.session_state.messages:
    role = "You" if message["role"] == "user" else "Claude"
    align_style = "text-align: right;" if role == "You" else "text-align: left;"
    st.markdown(f'<div style="{align_style}"><b>{role}:</b> {message["content"]}</div>', unsafe_allow_html=True)

# Chat input with file attachment
user_query = st.chat_input("Enter your message:", key="user_input")
if uploaded_file:
    st.session_state.uploaded_file = uploaded_file

# Process file upload
if st.session_state.uploaded_file is not None:
    encoded_data = base64.standard_b64encode(st.session_state.uploaded_file.getvalue()).decode("utf-8")
    file_extension = os.path.splitext(st.session_state.uploaded_file.name)[1]
    if file_extension == ".pdf":
        doc_type = "document"
        media_type_prefix = "application"
    elif file_extension in [".jpeg", ".png", ".webp"]:
        doc_type = "image"
        media_type_prefix = "image"

if user_query:
    if st.session_state.uploaded_file:
        content_for_hm = [
                {
                    "type": doc_type,
                    "source": {
                        "type": "base64",
                        "media_type": media_type_prefix + "/" + file_extension[1:],
                        "data": encoded_data
                    }
                },
                {
                    "type": "text",
                    "text": user_query if user_query else " "
                }
            ]
    else:
        content_for_hm = user_query

    # Add user input to chat history
    st.session_state.messages.append({"role": "user", "content": content_for_hm})

    st.markdown(f'<div style="text-align: right;"><b>You:</b> {user_query}</div>', unsafe_allow_html=True)

    thinking_configs = {"type": "enabled", "budget_tokens": thinking_token_budget} if thinking_mode else {"type": "disabled"}
    
    if thinking_mode:
        temperature = 1
    # Placeholder for streaming response
    response_placeholder = st.empty()
    full_response = ""
    
    # Initialize Claude models
    chat_model = client.beta.messages.stream(
        model="claude-3-7-sonnet-20250219",
        max_tokens=max_tokens,
        temperature=temperature,
        messages=st.session_state.messages,
        betas=["output-128k-2025-02-19"],
        thinking=thinking_configs
    )
    
    with chat_model as stream:
        for text in stream.text_stream:
            full_response += text or ""
            response_placeholder.markdown(f'<div style="text-align: left;"><b>Claude:</b><br>{full_response}</div>', unsafe_allow_html=True)
    
    # Add bot response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
    
    # Save messages to Firestore
    st.session_state.chat_sessions[st.session_state.current_chat]["messages"] = st.session_state.messages[:]
    save_chat_sessions()
    
    # Clear the uploaded file after processing
    st.session_state.uploaded_file = None
