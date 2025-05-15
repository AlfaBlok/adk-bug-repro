#%%
import requests
import json
import sys

# --- Global Variables for Session State ---
global_agent_name = 'multi_tool_agent'
global_user_id = 'u_interactive_test' 
global_session_id = 's_interactive_test' # Initial session ID, Cell 1 can update this

# --- Helper to print headers for common requests ---
common_headers = {
    "Content-Type": "application/json"
}

# --- Cell 1: Create a New Session --- 
def run_cell1():
    global global_agent_name, global_user_id, global_session_id # Allow modification of globals
    # print("--- Running Cell 1: Create a New Session ---")
    
    agent_input = input(f"Enter Agent Name (default: {global_agent_name}): ") or global_agent_name
    user_input = input(f"Enter User ID (default: {global_user_id}): ") or global_user_id
    session_input = input(f"Enter Session ID for new session (default: {global_session_id}): ") or global_session_id

    url_create_session = f"http://localhost:8000/apps/{agent_input}/users/{user_input}/sessions/{session_input}"
    data_create_session = {"state": {}}

    try:
        response = requests.post(url_create_session, headers=common_headers, data=json.dumps(data_create_session))
        if response.status_code == 400 and "Session already exists" in response.text:
            print(f"Session '{session_input}' already exists. Using this existing session for subsequent operations.")
            global_agent_name = agent_input
            global_user_id = user_input
            global_session_id = session_input
            print(response.json())
        elif response.ok:
            # response.raise_for_status() # .ok already checks for < 400
            print("New session creation successful:")
            global_agent_name = agent_input
            global_user_id = user_input
            global_session_id = session_input
            print(response.json())
        else:
            response.raise_for_status() # For other errors > 400
            print(f"New session creation returned: {response.status_code}")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error creating/validating session: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
    # print("--- Cell 1 End ---\n")

# --- Cell 2: Send a Query (using /run, non-streaming) ---
def run_cell2():
    print("--- Running Cell 2: Send a Query (using /run) ---")
    print(f"Using: Agent='{global_agent_name}', User='{global_user_id}', Session='{global_session_id}'")
    query_text_run = "weather in new york" # Preset query
    print(f"Using preset query: '{query_text_run}'")

    url_run = "http://localhost:8000/run"
    data_run = {
        "app_name": global_agent_name,
        "user_id": global_user_id,
        "session_id": global_session_id,
        "new_message": {"role": "user", "parts": [{"text": query_text_run}]}
    }
    try:
        response = requests.post(url_run, headers=common_headers, data=json.dumps(data_run))
        response.raise_for_status()
        print(f"Query response for '{query_text_run}' (using /run):")
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"Error sending query to /run: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
    # print("--- Cell 2 End ---\n")

# --- Cell 3: Stream Full JSON Events from /run_sse ---
def run_cell3():
    # print("--- Running Cell 3: Stream Full JSON Events from /run_sse ---")
    # print(f"Using: Agent='{global_agent_name}', User='{global_user_id}', Session='{global_session_id}'")
    query_text_sse = "slow weather in new york" # Preset query
    print(f"'{query_text_sse}'")
    
    url_sse = "http://localhost:8000/run_sse"
    headers_sse = {**common_headers, "Accept": "text/event-stream"}
    data_sse = {
        "app_name": global_agent_name,
        "user_id": global_user_id,
        "session_id": global_session_id,
        "new_message": {"role": "user", "parts": [{"text": query_text_sse}]},
        "streaming": True
    }
    try:
        print(f"Streaming full JSON response for '{query_text_sse}' (SSE enabled, to /run_sse):")
        with requests.post(url_sse, headers=headers_sse, data=json.dumps(data_sse), stream=True) as response:
            response.raise_for_status()
            buffer = b''
            for chunk in response.iter_content(chunk_size=None):
                if not chunk: continue
                buffer += chunk
                while True:
                    try: newline_pos = buffer.index(b'\n')
                    except ValueError: break
                    line_bytes = buffer[:newline_pos]
                    buffer = buffer[newline_pos+1:]
                    if not line_bytes.strip(): continue
                    try: decoded_line = line_bytes.decode('utf-8')
                    except UnicodeDecodeError: continue
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line[len('data: '):].strip()
                        if not json_str: continue
                        try:
                            event_data = json.loads(json_str)
                            print(json.dumps(event_data, indent=2)) # Print full JSON event
                        except json.JSONDecodeError:
                            sys.stderr.write(f"[Error] JSONDecodeError for: {json_str}\n")
        sys.stdout.write("\n") # Ensure prompt is on new line after stream
        sys.stdout.flush()
    except requests.exceptions.RequestException as e:
        print(f"Error sending streaming SSE query to /run_sse: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
    # print("--- Cell 3 End ---\n")

# --- Cell 4: Stream and Print Only Text Parts from /run_sse (showing build-up) ---
def run_cell4():
    # print("--- Running Cell 4: Stream and Print Only Text Parts from /run_sse (showing build-up) ---")
    # print(f"Using: Agent='{global_agent_name}', User='{global_user_id}', Session='{global_session_id}'")
    query_text_sse_text_only = "weather in new york" # Preset query
    print(f"'{query_text_sse_text_only}'")

    url_sse_text_only = "http://localhost:8000/run_sse"
    headers_sse_text_only = {**common_headers, "Accept": "text/event-stream"}
    data_sse_text_only = {
        "app_name": global_agent_name,
        "user_id": global_user_id,
        "session_id": global_session_id,
        "new_message": {"role": "user", "parts": [{"text": query_text_sse_text_only}]},
        "streaming": True
    }
    try:
        # print(f"Streaming only text parts for query '{query_text_sse_text_only}' (SSE enabled, to /run_sse):")
        # Tracks if the current line being printed has received any text from partials
        printed_partials_for_current_utterance = False 
        # Keep track of the very last piece of text printed to manage newlines correctly
        last_printed_text_segment = ""

        with requests.post(url_sse_text_only, headers=headers_sse_text_only, data=json.dumps(data_sse_text_only), stream=True) as response:
            response.raise_for_status()
            buffer = b''
            for chunk in response.iter_content(chunk_size=None):
                if not chunk: continue
                buffer += chunk
                while True:
                    try: newline_pos = buffer.index(b'\n')
                    except ValueError: break
                    line_bytes = buffer[:newline_pos]
                    buffer = buffer[newline_pos+1:]
                    if not line_bytes.strip(): continue
                    try: decoded_line = line_bytes.decode('utf-8')
                    except UnicodeDecodeError: continue
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line[len('data: '):].strip()
                        if not json_str: continue
                        try:
                            event_data = json.loads(json_str)
                            if event_data.get("content") and isinstance(event_data["content"].get("parts"), list):
                                for part_content in event_data["content"]["parts"]:
                                    if isinstance(part_content, dict) and "text" in part_content:
                                        text_from_event = part_content['text'].replace('\r', '')
                                        is_final_event = not event_data.get('partial', False)

                                        if not is_final_event: # This is a partial event (partial:true)
                                            if text_from_event:
                                                sys.stdout.write(text_from_event)
                                                sys.stdout.flush()
                                                printed_partials_for_current_utterance = True
                                                last_printed_text_segment = text_from_event
                                        else: # This is the final event for an utterance
                                            # If partials were printed, the final event's text is mostly for confirmation/completeness.
                                            # We only print its text if no partials were received for this utterance.
                                            if not printed_partials_for_current_utterance and text_from_event:
                                                sys.stdout.write(text_from_event)
                                                sys.stdout.flush()
                                                last_printed_text_segment = text_from_event
                                            
                                            # Ensure a newline after a completed utterance if the last printed part didn't end with one.
                                            if (printed_partials_for_current_utterance or text_from_event) and not last_printed_text_segment.endswith('\n'):
                                                sys.stdout.write('\n')
                                                sys.stdout.flush()
                                            
                                            printed_partials_for_current_utterance = False # Reset for next utterance
                                            last_printed_text_segment = "" # Reset
                                            
                        except json.JSONDecodeError:
                            sys.stderr.write(f"[Error] JSONDecodeError for: {json_str}\n")
        # After loop, if the last thing printed didn't end with a newline (e.g. stream cut off)
        if printed_partials_for_current_utterance and not last_printed_text_segment.endswith('\n'): 
            sys.stdout.write("\n")
            sys.stdout.flush()
            
    except NameError as ne:
        print(f"\n[Script Error] A variable was not defined. This might happen if Cell 1 was not run successfully. Details: {ne}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending streaming SSE query for text parts: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
    # print("--- Cell 4 End ---\n")

# --- Cell 5: Stream Text Parts from /run_sse using slow_get_weather tool ---
def run_cell5():
    # print("--- Running Cell 5: Stream Text Parts with slow_get_weather tool ---")
    # print(f"Using: Agent='{global_agent_name}', User='{global_user_id}', Session='{global_session_id}'")
    query_text_slow_weather = "get slow weather for new york" # Preset query to target the slow tool
    print(f"'{query_text_slow_weather}'")

    url_sse_slow = "http://localhost:8000/run_sse"
    headers_sse_slow = {**common_headers, "Accept": "text/event-stream"}
    data_sse_slow = {
        "app_name": global_agent_name,
        "user_id": global_user_id,
        "session_id": global_session_id,
        "new_message": {"role": "user", "parts": [{"text": query_text_slow_weather}]},
        "streaming": True
    }
    try:
        # print(f"Streaming only text parts for query '{query_text_slow_weather}' (SSE enabled, to /run_sse):")
        printed_partials_for_current_utterance = False 
        last_printed_text_segment = ""

        with requests.post(url_sse_slow, headers=headers_sse_slow, data=json.dumps(data_sse_slow), stream=True) as response:
            response.raise_for_status()
            buffer = b''
            for chunk in response.iter_content(chunk_size=None):
                if not chunk: continue
                buffer += chunk
                while True:
                    try: newline_pos = buffer.index(b'\n')
                    except ValueError: break
                    line_bytes = buffer[:newline_pos]
                    buffer = buffer[newline_pos+1:]
                    if not line_bytes.strip(): continue
                    try: decoded_line = line_bytes.decode('utf-8')
                    except UnicodeDecodeError: continue
                    if decoded_line.startswith('data: '):
                        json_str = decoded_line[len('data: '):].strip()
                        if not json_str: continue
                        try:
                            event_data = json.loads(json_str)
                            if event_data.get("content") and isinstance(event_data["content"].get("parts"), list):
                                for part_content in event_data["content"]["parts"]:
                                    if isinstance(part_content, dict) and "text" in part_content:
                                        text_from_event = part_content['text'].replace('\r', '')
                                        is_final_event = not event_data.get('partial', False)

                                        if not is_final_event: # This is a partial event (partial:true)
                                            if text_from_event:
                                                sys.stdout.write(text_from_event)
                                                sys.stdout.flush()
                                                printed_partials_for_current_utterance = True
                                                last_printed_text_segment = text_from_event
                                        else: # This is the final event for an utterance
                                            if not printed_partials_for_current_utterance and text_from_event:
                                                sys.stdout.write(text_from_event)
                                                sys.stdout.flush()
                                                last_printed_text_segment = text_from_event
                                            
                                            if (printed_partials_for_current_utterance or text_from_event) and not last_printed_text_segment.endswith('\n'):
                                                sys.stdout.write('\n')
                                                sys.stdout.flush()
                                            
                                            printed_partials_for_current_utterance = False 
                                            last_printed_text_segment = "" 
                                            
                        except json.JSONDecodeError:
                            sys.stderr.write(f"[Error] JSONDecodeError for: {json_str}\n")
        if printed_partials_for_current_utterance and not last_printed_text_segment.endswith('\n'): 
            sys.stdout.write("\n")
            sys.stdout.flush()
            
    except NameError as ne:
        print(f"\n[Script Error] A variable was not defined. This might happen if Cell 1 was not run successfully. Details: {ne}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending streaming SSE query for text parts: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")
    # print("--- Cell 5 End ---\n")

# --- Main Interactive Loop ---
def main():
    # Automatically run Cell 1 on script start to ensure session variables are set, 
    # or at least an attempt is made and user is informed.
    print("Initializing: Attempting to set up or validate session (equivalent to running Cell 1 first).")
    run_cell1() 
    print("Initialization complete. Main menu will now be shown.\n")

    while True:
        print("\nAvailable operations:")
        print("1. Create/Re-initialize Session (Cell 1)")
        print("2. Send Query to /run (Non-streaming) (Cell 2)")
        print("3. Stream Full JSON Events from /run_sse (Cell 3)")
        print("4. Stream Text Parts from /run_sse (showing build-up) (Cell 4)")
        print("5. Stream Text Parts using slow_get_weather (Cell 5)")
        print("exit. Exit the script")
        
        choice = input("Enter your choice (1-5 or exit): ").strip().lower()
        
        if choice == '1':
            run_cell1()
        elif choice == '2':
            run_cell2()
        elif choice == '3':
            run_cell3()
        elif choice == '4':
            run_cell4()
        elif choice == '5':
            run_cell5()
        elif choice == 'exit':
            print("Exiting script.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()

print("Python script execution finished.") 
# %%
