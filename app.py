import streamlit as st
import shelve
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, AIMessage

# Set up Streamlit UI
st.set_page_config(page_title="Claude Chatbot", layout="wide")
st.title("Chat with Claude AI")

# Load chat history from shelve
def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("chat_sessions", [])

def save_chat_history():
    with shelve.open("chat_history") as db:
        db["chat_sessions"] = st.session_state.chat_sessions

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = load_chat_history()
if "current_chat" not in st.session_state:
    st.session_state.current_chat = "New Chat"

# Sidebar settings
st.sidebar.header("Settings")
max_tokens = st.sidebar.slider("Max Tokens", min_value=50, max_value=4096, value=1700)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.05)
thinking_mode = st.sidebar.toggle("Thinking Mode", value=True)
thinking_token_budget = st.sidebar.slider("Thinking Token Budget", min_value=50, max_value=4096, value=1024)

st.sidebar.header("Chat History")

# Function to start a new chat session
def start_new_chat():
    if st.session_state.messages:
        st.session_state.chat_sessions.insert(0, {  # Insert at the top
            "name": f"Chat {len(st.session_state.chat_sessions) + 1}",
            "messages": st.session_state.messages.copy()
        })
        save_chat_history()
    st.session_state.messages = []
    st.session_state.current_chat = f"Chat {len(st.session_state.chat_sessions) + 1}"

# Button to start a new chat
if st.sidebar.button("New Chat"):
    start_new_chat()

# Display past chat sessions in sidebar (latest first)
for chat in st.session_state.chat_sessions:
    if st.sidebar.button(chat["name"]):
        st.session_state.messages = chat["messages"].copy()
        st.session_state.current_chat = chat["name"]

# Load API key from Streamlit secrets
api_key_claude = st.secrets["ANTHROPIC_API_KEY"]

# Display chat history with alignment styles
for message in st.session_state.messages:
    role = "You" if isinstance(message, HumanMessage) else "Claude"
    align_style = "text-align: right;" if role == "You" else "text-align: left;"
    st.markdown(f'<div style="{align_style}"><b>{role}:</b> {message.content}</div>', unsafe_allow_html=True)

# User input
user_query = st.chat_input("Enter your message:")

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
    # Add user input to chat history
    st.session_state.messages.append(HumanMessage(content=user_query))
    
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
    if thinking_mode:
        st.session_state.messages.append(AIMessage(content=text_blocks))
    else:
        st.session_state.messages.append(AIMessage(content=bot_reply))
    
    # Save updated chat history
    save_chat_history()
    
    # Display response with alignment
    st.markdown(f'<div style="text-align: right;"><b>You:</b> {user_query}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="text-align: left;"><b>Claude:</b><br>{bot_reply}</div>', unsafe_allow_html=True)
