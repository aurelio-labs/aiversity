import streamlit as st
import os
import json
import re
import time
from datetime import datetime


def load_json_file(file_path):
    with open(file_path, "r") as file:
        return json.load(file)


def color_json(json_str):
    colors = {
        "key": "#79c0ff",
        "string": "#a5d6ff",
        "number": "#ffa657",
        "boolean": "#ff7b72",
        "null": "#ff7b72",
        "brace": "#c9d1d9",
    }

    def colorize(match):
        token = match.group(0)
        if ":" in token:
            key = token.split(":")[0].strip('"')
            return f'<span style="color: {colors["key"]}">{key}</span>:'
        elif token.startswith('"'):
            return f'<span style="color: {colors["string"]}">{token}</span>'
        elif token in ("true", "false"):
            return f'<span style="color: {colors["boolean"]}">{token}</span>'
        elif token == "null":
            return f'<span style="color: {colors["null"]}">{token}</span>'
        elif token in "{}[]":
            return f'<span style="color: {colors["brace"]}">{token}</span>'
        else:  # number
            return f'<span style="color: {colors["number"]}">{token}</span>'

    regex = r'("[^"]*")\s*:|"[^"]*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null|[{}\[\]]'
    return re.sub(regex, colorize, json_str)


def format_json(data):
    def format_value(v):
        if isinstance(v, str):
            return html_escape(v).replace("\n", "<br>")
        elif isinstance(v, (dict, list)):
            return json.dumps(v, indent=2, ensure_ascii=False)
        else:
            return json.dumps(v)

    def format_dict(d, indent=0):
        result = []
        for k, v in d.items():
            if isinstance(v, dict):
                result.append(f'{"&nbsp;" * indent}"{k}": {{')
                result.append(format_dict(v, indent + 2))
                result.append(f'{"&nbsp;" * indent}}}')
            elif isinstance(v, list):
                result.append(f'{"&nbsp;" * indent}"{k}": [')
                for item in v:
                    if isinstance(item, dict):
                        result.append(f'{"&nbsp;" * (indent + 2)}{{')
                        result.append(format_dict(item, indent + 4))
                        result.append(f'{"&nbsp;" * (indent + 2)}}},')
                    else:
                        result.append(f'{"&nbsp;" * (indent + 2)}{format_value(item)},')
                result.append(f'{"&nbsp;" * indent}]')
            else:
                result.append(f'{"&nbsp;" * indent}"{k}": {format_value(v)},')
        return "<br>".join(result)

    formatted_json = format_dict(data)
    return color_json(f"<pre>{formatted_json}</pre>")


def html_escape(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def get_log_files():
    log_folder = "llm_logs"
    files = [f for f in os.listdir(log_folder) if f.endswith(".json")]
    return sorted(
        files, key=lambda x: os.path.getmtime(os.path.join(log_folder, x)), reverse=True
    )


st.set_page_config(layout="wide", page_title="LLM Log Viewer")

st.title("Lumos")

# Sidebar for options
st.sidebar.header("Options")

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)

# Manual refresh button
if st.sidebar.button("Refresh Now"):
    st.experimental_rerun()

# Get log files
log_files = get_log_files()

# File selection
st.sidebar.header("Select Log File")
for file in log_files:
    file_path = os.path.join("llm_logs", file)
    timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    if st.sidebar.button(f"{timestamp} - {file}", key=file):
        st.session_state.selected_file = file

# Main content area
if "selected_file" in st.session_state and st.session_state.selected_file in log_files:
    file_path = os.path.join("llm_logs", st.session_state.selected_file)
    data = load_json_file(file_path)

    # Display request and response
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Request")
        request_html = format_json(data["request"])
        st.markdown(
            f'<div class="json-content">{request_html}</div>', unsafe_allow_html=True
        )

    with col2:
        st.subheader("Response")
        response_html = format_json(data["response"])
        st.markdown(
            f'<div class="json-content">{response_html}</div>', unsafe_allow_html=True
        )

    # Add custom CSS for better formatting
    st.markdown(
        """
    <style>
    .json-content {
        background-color: #0d1117;
        color: #c9d1d9;
        padding: 10px;
        border-radius: 5px;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.7em;
        white-space: pre-wrap;
        word-wrap: break-word;
        max-height: 80vh;
        overflow-y: auto;
    }
    .json-content pre {
        margin: 0;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

else:
    st.write("No file selected. Please choose a file from the sidebar.")

# Auto-refresh logic
if auto_refresh:
    time.sleep(5)  # Wait for 5 seconds
    st.experimental_rerun()
