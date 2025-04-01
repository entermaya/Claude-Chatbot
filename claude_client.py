import streamlit as st
import anthropic
from typing import List, Dict, Any

class ClaudeClient:
    def __init__(self, api_key: str):
        """Initialize the Claude client with API key."""
        self.client = anthropic.Anthropic(api_key=api_key)
        
    def stream_response(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int,
        temperature: float,
        thinking_mode: bool,
        thinking_token_budget: int
    ) -> str:
        """
        Stream the response from Claude model.
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens for the response
            temperature: Temperature setting for the model
            thinking_mode: Whether thinking mode is enabled
            thinking_token_budget: Token budget for thinking mode
            
        Returns:
            The complete response as a string
        """
        thinking_configs = {"type": "enabled", "budget_tokens": thinking_token_budget} if thinking_mode else {"type": "disabled"}
        
        if thinking_mode:
            temperature = 1
            
        # Initialize Claude models
        chat_model = self.client.beta.messages.stream(
            model="claude-3-7-sonnet-20250219",
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            betas=["output-128k-2025-02-19"],
            thinking=thinking_configs
        )
        
        # Placeholder for streaming response
        response_placeholder = st.empty()

        full_response = ""
        with chat_model as stream:
            for text in stream.text_stream:
                full_response += text or ""
                response_placeholder.markdown(f'<div style="text-align: left;"><b>Claude:</b><br>{full_response}</div>', unsafe_allow_html=True)
        
        return full_response 