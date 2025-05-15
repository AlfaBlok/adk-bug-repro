import streamlit as st
import requests
import json
import time # For unique keys or other purposes

# Initialize session state variables
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'last_event_id' not in st.session_state:
    st.session_state.last_event_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_query_active' not in st.session_state:
    st.session_state.current_query_active = False
if 'prompt_to_process' not in st.session_state:
    st.session_state.prompt_to_process = None

def create_session(server_url):
    """Creates a new session with the ADK agent."""
    try:
        st.session_state.current_query_active = False # Reset query flag
        response = requests.post(f"{server_url}/session")
        response.raise_for_status()
        session_data = response.json()
        st.session_state.session_id = session_data.get("session_id")
        st.session_state.last_event_id = None
        st.session_state.chat_history = [] # Clear history for new session
        st.session_state.prompt_to_process = None # Clear any pending prompt
        st.success(f"Session created successfully! Session ID: {st.session_state.session_id}")
    except requests.exceptions.RequestException as e:
        st.error(f"Error creating session: {e}")
        st.session_state.session_id = None

def process_agent_response_stream(server_url, question):
    """Processes the streaming response from the ADK agent for the chat."""
    if not st.session_state.session_id:
        st.error("Session not created. Please create a session first.")
        st.session_state.current_query_active = False
        return

    headers = {"Accept": "text/event-stream"}
    params = {
        "session_id": st.session_state.session_id,
        "question": question,
        "streaming": "true"
    }
    if st.session_state.last_event_id:
        headers["Last-Event-ID"] = str(st.session_state.last_event_id)

    url = f"{server_url}/run_sse"
    
    assistant_message_idx = len(st.session_state.chat_history)
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": "", # Initial content, will be built by build_display_text
        "raw_events": [], 
        "utterances": {}, # To store text, partial_received, final_text_set per utterance_id
        "current_display_text": "▌" # Initial display with cursor
    })
    # Initial rerun to show the assistant placeholder with a cursor
    st.rerun()


    current_utterance_id_streaming = None # Renamed to avoid conflict
    
    try:
        with requests.get(url, headers=headers, params=params, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not st.session_state.current_query_active:
                    print("Stream stopped as current_query_active is false.")
                    break 
                if line:
                    decoded_line = line.decode('utf-8')
                    # Ensure assistant_message_idx is still valid (e.g. session not reset)
                    if assistant_message_idx >= len(st.session_state.chat_history) or \
                       st.session_state.chat_history[assistant_message_idx]["role"] != "assistant":
                        print("Chat history changed unexpectedly. Aborting stream processing for this message.")
                        break
                    
                    current_message_entry = st.session_state.chat_history[assistant_message_idx]
                    current_message_entry["raw_events"].append(decoded_line)

                    if decoded_line.startswith("data:"):
                        try:
                            event_data_str = decoded_line[len("data:"):]
                            event_data = json.loads(event_data_str)
                            
                            st.session_state.last_event_id = event_data.get("id")
                            event_type = event_data.get("event")
                            data = event_data.get("data", {})
                            utterance_id_from_event = data.get("utterance_id")

                            if utterance_id_from_event and utterance_id_from_event != current_utterance_id_streaming:
                                current_utterance_id_streaming = utterance_id_from_event
                                if current_utterance_id_streaming not in current_message_entry["utterances"]:
                                    current_message_entry["utterances"][current_utterance_id_streaming] = \
                                        {"text": "", "partial_received": False, "final_text_set": False}
                            
                            utt_data = current_message_entry["utterances"].get(current_utterance_id_streaming)

                            if event_type == "speak":
                                text = data.get("text", "")
                                partial = data.get("partial", False)
                                if utt_data:
                                    utt_data["text"] = text # ADK often sends cumulative text for partials
                                    if partial:
                                        utt_data["partial_received"] = True
                                        utt_data["final_text_set"] = False
                                    else: # Final event for this speak
                                        utt_data["final_text_set"] = True
                                else: # Fallback if speak event has no utterance_id context
                                    current_message_entry["content"] += text + ("" if partial else "\n")


                            elif event_type == "tool_code":
                                tool_name = data.get("tool_name")
                                tool_input_str = data.get("tool_input", "{}")
                                tool_msg = f'''\n*Executing tool: `{tool_name}` with input:*\n```json\n{tool_input_str}\n```\n'''
                                if utt_data: utt_data["text"] += tool_msg
                                else: current_message_entry["content"] += tool_msg
                            
                            elif event_type == "tool_result":
                                tool_name = data.get("tool_name")
                                tool_output_str = data.get("tool_output", "{}")
                                result_msg = f'''\n*Tool `{tool_name}` result:*\n```json\n{tool_output_str}\n```\n'''
                                if utt_data: utt_data["text"] += result_msg
                                else: current_message_entry["content"] += result_msg

                            elif event_type == "error":
                                error_message = data.get("message", "Unknown error")
                                error_msg_display = f"\n**Agent error:** {error_message}"
                                if utt_data: utt_data["text"] += error_msg_display
                                else: current_message_entry["content"] += error_msg_display
                                st.session_state.current_query_active = False
                            
                            elif event_type == "end":
                                if utt_data and not utt_data["final_text_set"]:
                                    utt_data["final_text_set"] = True 
                                st.session_state.current_query_active = False


                            current_message_entry["current_display_text"] = build_display_text(current_message_entry)
                            st.rerun()
                            
                            if event_type == "end" or event_type == "error":
                                return # Exit processing loop

                        except json.JSONDecodeError:
                            current_message_entry["raw_events"].append(f"Could not parse JSON: {event_data_str}")
                            st.rerun()
                        except Exception as e:
                            error_info = f"Error processing event: {e} - Line: {decoded_line}"
                            current_message_entry["raw_events"].append(error_info)
                            current_message_entry["content"] += f"\n{error_info}" # Add to visible content
                            current_message_entry["current_display_text"] = build_display_text(current_message_entry, final_pass=True)
                            st.error(f"Stream error: {e}") 
                            st.session_state.current_query_active = False
                            st.rerun()
                            return
            
            # Stream ended naturally if loop finishes
            st.session_state.current_query_active = False
            if assistant_message_idx < len(st.session_state.chat_history):
                current_message_entry = st.session_state.chat_history[assistant_message_idx]
                # Mark all utterances as final if not already, just in case ADK stream ends without final partial=false
                for utt_id_key in current_message_entry["utterances"]:
                    if not current_message_entry["utterances"][utt_id_key]["final_text_set"]:
                        current_message_entry["utterances"][utt_id_key]["final_text_set"] = True
                current_message_entry["current_display_text"] = build_display_text(current_message_entry, final_pass=True)
            st.rerun()


    except requests.exceptions.HTTPError as e:
        err_msg = f"HTTP Error: {e.response.status_code} {e.response.reason}"
        st.error(err_msg)
        # st.text(e.response.text) # Can be too verbose
        st.session_state.current_query_active = False
        if assistant_message_idx < len(st.session_state.chat_history):
            st.session_state.chat_history[assistant_message_idx]["content"] = err_msg
            st.session_state.chat_history[assistant_message_idx]["current_display_text"] = err_msg
        st.rerun()
    except requests.exceptions.RequestException as e:
        err_msg = f"Error querying agent: {e}"
        st.error(err_msg)
        st.session_state.current_query_active = False
        if assistant_message_idx < len(st.session_state.chat_history):
            st.session_state.chat_history[assistant_message_idx]["content"] = err_msg
            st.session_state.chat_history[assistant_message_idx]["current_display_text"] = err_msg
        st.rerun()
    finally:
        # Ensure query active is false and final display update
        st.session_state.current_query_active = False
        if assistant_message_idx < len(st.session_state.chat_history) and \
           st.session_state.chat_history[assistant_message_idx]["role"] == "assistant":
            current_message_entry = st.session_state.chat_history[assistant_message_idx]
            current_message_entry["current_display_text"] = build_display_text(current_message_entry, final_pass=True)
        # Final rerun to clean up cursor etc.
        st.rerun()


def build_display_text(assistant_message_entry, final_pass=False):
    """Constructs the text to display for an assistant message from its utterances."""
    parts = []
    # Sort by first appearance if utterance_ids are not strictly ordered numbers
    # For now, assuming they are received in a somewhat logical order or ADK handles it.
    # Or, one could sort keys if they are sortable e.g. utterance_1, utterance_2
    
    sorted_utterance_ids = sorted(assistant_message_entry["utterances"].keys())

    for utt_id in sorted_utterance_ids: 
        utt_data = assistant_message_entry["utterances"][utt_id]
        text_to_display = utt_data["text"]
        # Add cursor only if it's the very last part of the overall message and it's still partial
        # This logic is simplified: cursor is shown if any part is streaming and it's the last one.
        # More precise: only the last utterance that is partial should have a cursor.
        # This function builds the full text. Cursor handling will be at the end.
        parts.append(text_to_display)
    
    full_text = "".join(parts) # Join all utterance texts. ADK usually provides cumulative text or distinct segments.

    # Add any content that wasn't part of an utterance (e.g. initial errors, or simple non-utterance messages)
    if not assistant_message_entry["utterances"] and assistant_message_entry["content"]:
        full_text = assistant_message_entry["content"] + full_text # Prepend or append as makes sense

    # Determine if a cursor should be shown
    show_cursor = False
    if not final_pass and st.session_state.current_query_active:
        if sorted_utterance_ids:
            last_utt_id = sorted_utterance_ids[-1]
            if not assistant_message_entry["utterances"][last_utt_id]["final_text_set"]:
                show_cursor = True
        elif not full_text: # No utterances and no text yet, but query is active (initial state)
             show_cursor = True


    return full_text + ("▌" if show_cursor else "")


# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title("ADK Agent Chat Client")

st.sidebar.header("Connection")
server_url = st.sidebar.text_input("ADK Server URL", "http://localhost:8000", key="server_url_input")

if st.sidebar.button("Create New Session", key="new_session_button"):
    create_session(server_url)
    st.rerun() # Rerun to reflect session status and clear chat

if st.session_state.session_id:
    st.sidebar.success(f"Active Session: {st.session_state.session_id[:8]}...", icon="✅")
else:
    st.sidebar.warning("No active session.", icon="⚠️")
    if server_url and 'first_run_done' not in st.session_state: # Auto-create on first proper run with URL
        create_session(server_url)
        st.session_state.first_run_done = True # Ensure this only happens once automatically
        if st.session_state.session_id: st.rerun() 

# Display chat messages
st.header("Chat")
for i, message in enumerate(st.session_state.chat_history):
    with st.chat_message(message["role"]):
        display_content = message.get("current_display_text", message["content"])
        st.markdown(display_content)
        
        if message["role"] == "assistant" and message.get("raw_events"):
            with st.expander(f"Show Raw Events (Assistant Message {i+1})", expanded=False):
                # Display raw events as a list of strings for readability
                st.text("\n".join(message["raw_events"]))


# Handle chat input and processing trigger
if prompt_from_input := st.chat_input("What is your question?", 
                                       disabled=st.session_state.current_query_active, 
                                       key="chat_input_main"):
    if not st.session_state.session_id:
        st.error("Please ensure a session is active before sending a message.")
    else:
        st.session_state.chat_history.append({"role": "user", "content": prompt_from_input})
        st.session_state.current_query_active = True
        st.session_state.prompt_to_process = prompt_from_input # Flag to process this prompt
        st.rerun() # Show user message, then next run will trigger processing


if st.session_state.prompt_to_process and st.session_state.current_query_active:
    prompt_to_run = st.session_state.prompt_to_process
    st.session_state.prompt_to_process = None # Clear the flag
    process_agent_response_stream(server_url, prompt_to_run)
    # process_agent_response_stream handles its own reruns and eventually sets current_query_active to False


# Status indicator when agent is responding
if st.session_state.current_query_active and not st.session_state.prompt_to_process:
    # Check if the last message is an assistant message that is still being built
    if st.session_state.chat_history and \
       st.session_state.chat_history[-1]["role"] == "assistant" and \
       "▌" in st.session_state.chat_history[-1].get("current_display_text", ""):
        st.info("Agent is responding...")
    elif not st.session_state.chat_history or st.session_state.chat_history[-1]["role"] == "user":
        # This implies current_query_active but assistant placeholder not yet added by process_agent_response_stream
        # This state should be very brief due to the immediate rerun in process_agent_response_stream
        pass


st.markdown("---")
st.markdown('''
### Notes on Streaming Logic:
- **Chat Interface**: User questions and agent responses are displayed sequentially. `st.chat_message` is used for styling.
- **Real-time Updates**: Agent responses are updated live as text streams in. A `▌` cursor indicates ongoing generation for the assistant's message.
- **Utterance Handling**: The app groups related pieces of text using `utterance_id` from ADK events. Each utterance is built up from partials (where ADK often sends cumulative text for a given partial `speak` event) and then finalized. Tool calls and results are interspersed.
- **`st.rerun()` Strategy**:
    - User submits input: Add to history, set `prompt_to_process` flag, `st.rerun()`.
    - Script reruns: User message is displayed. `prompt_to_process` flag triggers `process_agent_response_stream`.
    - `process_agent_response_stream` adds an assistant message placeholder to history and calls `st.rerun()` to show it (often just the cursor initially).
    - As SSE events arrive, `process_agent_response_stream` updates the assistant's message in `st.session_state.chat_history` and calls `st.rerun()` to refresh the display.
    - On stream `end` or `error`, or if the stream connection closes, `current_query_active` is set to `False`, and a final `st.rerun()` ensures the UI is clean.
- **Raw JSON Events**: Each assistant message has an expandable section to view the raw SSE events.
- **Session Management**: A session can be created via a sidebar button. A new session clears chat history. An attempt to auto-create a session is made on the first load if a server URL is present.
''')

