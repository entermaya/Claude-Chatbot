import streamlit as st
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, AIMessage
import os
import copy
import base64

# Set up Streamlit UI
st.set_page_config(page_title="Claude Chatbot", layout="wide")
st.title("Chat with Claude AI")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = [{"name": "Chat 1", "messages": []}]
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "Chat 1"
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# Sidebar settings
st.sidebar.header("Settings")
max_tokens = st.sidebar.slider("Max Tokens", min_value=1024, max_value=100000, value=1700)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
thinking_mode = st.sidebar.toggle("Thinking Mode", value=True)
thinking_token_budget = st.sidebar.slider("Thinking Token Budget", min_value=1024, max_value=4096, value=1048)

st.sidebar.header("Chat History")

# Function to start a new chat session
def start_new_chat():
    new_chat_name = f"Chat {len(st.session_state.chat_sessions) + 1}"
    st.session_state.chat_sessions.insert(0, {  # Insert at the top
        "name": new_chat_name,
        "messages": []  # Start fresh
    })
    st.session_state.messages = []
    st.session_state.current_chat = new_chat_name
    st.session_state.uploaded_file = None  # Reset file input

# Button to start a new chat
if st.sidebar.button("New Chat"):
    start_new_chat()

# Display past chat sessions in sidebar (latest first)
for i, chat in enumerate(st.session_state.chat_sessions):
    if st.sidebar.button(chat["name"], key=f"chat_{i}"):
        st.session_state.messages = copy.deepcopy(chat["messages"])  # Deep copy to avoid overwriting previous chats
        st.session_state.current_chat = chat["name"]
        st.session_state.uploaded_file = None  # Reset file input when switching chats

# Load API key from Streamlit secrets
api_key_claude = st.secrets["ANTHROPIC_API_KEY"]

# Display chat history with alignment styles
for message in st.session_state.messages:
    role = "You" if isinstance(message, HumanMessage) else "Claude"
    align_style = "text-align: right;" if role == "You" else "text-align: left;"
    st.markdown(f'<div style="{align_style}"><b>{role}:</b> {message.content}</div>', unsafe_allow_html=True)

# Chat input with file attachment
user_query = st.chat_input("Enter your message:", key="user_input")
uploaded_file = st.file_uploader("Attach a file", type=["pdf", "jpeg", "png", "webp"], label_visibility="collapsed")
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

# Initialize Claude models
chat_model = ChatAnthropic(
    model_name="claude-3-7-sonnet-20250219",
    max_tokens=max_tokens,
    temperature=temperature,
    api_key=api_key_claude
)

chat_model_thinking = ChatAnthropic(
    model_name="claude-3-7-sonnet-20250219",
    max_tokens=max_tokens,
    temperature=1,
    api_key=api_key_claude,
    thinking={"type": "enabled", "budget_tokens": thinking_token_budget}
)

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
    st.session_state.messages.append(HumanMessage(content=content_for_hm))
    
    # Select model based on thinking mode
    model_to_use = chat_model_thinking if thinking_mode else chat_model
    
    # Generate response with context
    response = model_to_use(st.session_state.messages)
    
    # Extract relevant content
    if thinking_mode:
        thinking_blocks = response.content[0]["thinking"]
        text_blocks = response.content[1]["text"]
        bot_reply = f"**Thinking:**\n{thinking_blocks}\n\n\n\n{text_blocks}"
    else:
        bot_reply = response.content if isinstance(response, AIMessage) else "Error generating response."
    
    # Add bot response to chat history
    st.session_state.messages.append(AIMessage(content=bot_reply))
    
    # Save messages to the correct chat session
    for chat in st.session_state.chat_sessions:
        if chat["name"] == st.session_state.current_chat:
            chat["messages"] = copy.deepcopy(st.session_state.messages)
            break
    
    # Display response with alignment
    st.markdown(f'<div style="text-align: right;"><b>You:</b> {user_query}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align: left;"><b>Claude:</b><br>{bot_reply}</div>', unsafe_allow_html=True)
    
    # Clear the uploaded file after processing
    st.session_state.uploaded_file = None
