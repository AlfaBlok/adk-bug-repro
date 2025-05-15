# ADK Streaming and Tool Behavior Test Script

This project contains a Python script (`bug_reproduction_script.py`) designed to test and observe the behavior of Google's Agent Development Kit (ADK), specifically focusing on:

*   Session management.
*   Streaming responses from an agent (`/run_sse` endpoint).
*   How agents handle tools, including tools with artificial delays (synchronous `time.sleep()`).
*   Parsing and displaying streamed text from the agent.

The script interacts with a sample ADK agent defined in the `multi_tool_agent/` directory.

## Prerequisites

1.  **Python Environment**: Ensure you have Python installed.
2.  **ADK Installed**: The `google-adk` library and its dependencies must be installed in your Python environment. You can typically install it via pip:
    ```bash
    pip install google-adk
    ```
3.  **Requests Library**: The script uses the `requests` library.
    ```bash
    pip install requests
    ```
4.  **ADK Agent**: The sample agent code is located in the `multi_tool_agent` directory. No specific modifications are needed beyond what's in the repository for the script to run, but its behavior (especially tool definitions) is what's being tested.

## Running the Test Script

1.  **Start the ADK API Server**:
    Open a terminal, navigate to the root directory of this project (`adk-bug-repro`), and start the ADK server:
    ```bash
    adk api_server
    ```
    You should see output indicating the server has started, typically running on `http://0.0.0.0:8000`.
    **Keep this server running in its terminal window.**

2.  **Run the Python Test Script**:
    Open a *new* terminal window, navigate to the root directory of this project, and run:
    ```bash
    python bug_reproduction_script.py
    ```

## Script Operations

Upon starting, the script will first attempt to initialize or validate a session with the ADK agent (equivalent to running Option 1). You will be prompted for Agent Name, User ID, and Session ID (defaults are provided).

After initialization, an interactive menu will appear with the following options:

1.  **Create/Re-initialize Session (Cell 1)**:
    *   Prompts for Agent Name, User ID, and Session ID.
    *   Attempts to create a new session with the ADK server using these details.
    *   If a session with the given ID already exists, it will confirm this and use the existing session details for subsequent operations in the script.
    *   Updates the script's global session parameters upon successful creation or validation.

2.  **Send Query to /run (Non-streaming) (Cell 2)**:
    *   Uses the preset query: `"weather in new york"`.
    *   Sends this query to the ADK agent's `/run` endpoint.
    *   Receives the complete JSON response from the agent at once (non-streaming).
    *   Prints the full, pretty-printed JSON response.

3.  **Stream Full JSON Events from /run_sse (Cell 3)**:
    *   Uses the preset query: `"weather in new york"`.
    *   Sends this query to the ADK agent's `/run_sse` endpoint with streaming enabled.
    *   Prints the **full JSON structure of each event** as it is received from the server.
    *   Useful for inspecting the raw event data, including `partial` flags, `functionCall`, `functionResponse`, etc.

4.  **Stream Text Parts from /run_sse (showing build-up) (Cell 4)**:
    *   Uses the preset query: `"weather in new york"`.
    *   Sends this query to the `/run_sse` endpoint with streaming enabled.
    *   Parses the events to extract and print **only the textual content** from the agent's responses.
    *   Attempts to display the text as it builds up, showing intermediate partial text chunks and then the final complete utterance from the agent.
    *   Newlines are managed to separate distinct utterances.

5.  **Stream Text Parts using slow_get_weather (Cell 5)**:
    *   Uses the preset query: `"get slow weather for new york"` (designed to trigger the `slow_get_weather` tool in the agent, which has an artificial 5-second delay).
    *   Otherwise, behaves identically to Option 4 in how it processes and displays the streamed text parts.
    *   This option is specifically for testing agent and tool behavior when a tool introduces a synchronous delay.

**exit**: Exits the script.

## Purpose of the Agent (`multi_tool_agent/agent.py`)

The agent is configured with a few tools:
*   `get_weather`: A tool to get the weather (typically fast).
*   `slow_get_weather`: A tool to get the weather with an intentional 5-second `time.sleep()` delay, used to test how the ADK runtime handles synchronous blocking calls within tools during streaming.
*   `get_current_time`: A tool to get the current time in a city.

The agent's instructions guide it on when and how to use these tools, including informing the user before calling a potentially slow tool.

This setup allows for focused testing of the ADK's behavior under different conditions, particularly with respect to streaming and tool execution latency. 