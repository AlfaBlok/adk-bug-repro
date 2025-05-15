# Testing Custom Client Consumption of ADK Streaming

**Objective**: To test if a custom Python client can effectively connect to a Google ADK `api_server`, consume its `/run_sse` streaming endpoint, and correctly process different event types, including partial text updates and responses from tools that may introduce delays.

**Key Questions Explored**:
*   Can a client connect to `/run_sse` and parse Server-Sent Events (SSE)?
*   How can `"partial": true` events be handled to create a progressive, non-duplicative text display?
*   What is the observed behavior when an agent tool introduces a synchronous delay (e.g., `time.sleep()`)?
*   Is it feasible to build responsive custom front-ends for ADK agents without relying on proprietary ADK front-end components?

This project uses `bug_reproduction_script.py` to interact with the `multi_tool_agent/` and `streamlit_app.py` as a simple web UI.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run ADK Server**: In the project root, start the ADK agent's API server. This typically serves the `multi_tool_agent/`.
    ```bash
    adk api_server
    ```
    (Ensure the `multi_tool_agent` is the one being served, or adjust agent path as needed).
3.  **Run Test Script or Streamlit App**:
    *   For the command-line script:
        ```bash
        python bug_reproduction_script.py
        ```
    *   For the Streamlit web application:
        ```bash
        streamlit run streamlit_app.py
        ```

## Test Script (`bug_reproduction_script.py`)

The script first automatically creates/validates an ADK session and then presents a menu for the following operations:

1.  **Session Init**: (Automatic on start) Ensures an active session with the ADK server.
2.  **/run Query (Non-Streaming)**:
    *   Sends a non-streaming query to the `/run` endpoint (preset: "weather in new york").
    *   Prints the full, single JSON response from the agent.
3.  **Full SSE Stream from /run_sse**:
    *   Sends a streaming query to `/run_sse` (preset: "weather in new york").
    *   Prints each raw JSON event received from the server. This is useful for understanding the structure of ADK's SSE messages.
    *   **Sample Event Sequence (Illustrative for Cell 3 output):**
        ```json
        data: {"id": 1, "event": "speak", "data": {"text": "I can help with that. ", "partial": true, "utterance_id": "utterance_1"}}

        data: {"id": 2, "event": "speak", "data": {"text": "I can help with that. I am about to retrieve the weather information for New York.", "partial": true, "utterance_id": "utterance_1"}}

        data: {"id": 3, "event": "tool_code", "data": {"tool_name": "get_weather", "tool_input": "{\"location\": \"New York\"}", "utterance_id": "utterance_1"}}

        # ... (ADK sends an ack for tool_code if client sends one) ...

        data: {"id": 4, "event": "tool_result", "data": {"tool_name": "get_weather", "tool_output": "{\"weather\": \"Sunny, 75F\"}", "utterance_id": "utterance_1"}}

        data: {"id": 5, "event": "speak", "data": {"text": "The weather in New York is Sunny, 75F.", "partial": false, "utterance_id": "utterance_1"}}

        data: {"id": 6, "event": "end", "data": {}}
        ```
4.  **Streamed Text (Fast Tool)**:
    *   Queries `/run_sse` (preset: "weather in new york") and processes events to display only the textual parts of the agent's response.
    *   Demonstrates handling of partial updates for a standard (fast) tool.
5.  **Streamed Text (Slow Tool)**:
    *   Similar to Option 4, but uses a query ("get slow weather for new york") designed to trigger the `slow_get_weather` tool, which includes a 5-second `time.sleep()`.
    *   Tests client-side handling of streaming when tool execution is delayed.

**Streaming Logic for Text (Options 4 & 5 and Streamlit App):**
The core strategy to display streamed text without duplication and show its build-up is as follows:
*   **Track Current Utterance**: An `utterance_id` is present in most relevant events (`speak`, `tool_code`, `tool_result`). Text accumulation is typically scoped to a single `utterance_id`.
*   **Handle Partial `speak` Events**:
    *   A variable (e.g., `current_utterance_text`) stores the text accumulated for the current `utterance_id`.
    *   When a `speak` event with `"partial": true` arrives:
        *   The new text (`event.data.text`) is often cumulative. The script calculates the "delta" (the part of the text not yet seen) by comparing the incoming text with `current_utterance_text`.
        *   This delta is appended to `current_utterance_text`.
        *   The display is updated (e.g., printing `current_utterance_text` with a carriage return `\r` and `end=''` in the script, or updating a Streamlit element).
    *   A flag (e.g., `partial_received_for_utterance`) is set to true.
*   **Handle Final `speak` Events**:
    *   When a `speak` event with `"partial": false` (or `partial` missing) arrives:
        *   If `partial_received_for_utterance` is `false` (meaning no partials came for this specific utterance before this final event), the full text from this event is printed directly.
        *   If `partial_received_for_utterance` is `true`, the script typically relies on the accumulated `current_utterance_text`. However, it's good practice to check if the final event's text differs from the accumulated one and update if necessary (ADK might send a correction).
        *   The full line is printed, followed by a newline.
    *   The `current_utterance_text` and `partial_received_for_utterance` are reset for the *next* utterance.
*   **Tool Events**: `tool_code` and `tool_result` events are printed informatively when they arrive.
*   **End Event**: Signals the completion of the agent's turn.

This logic aims to show text building up progressively (like someone typing) and then finalize it, while also interspersing tool activity messages.

## Agent (`multi_tool_agent/agent.py`)

The test agent includes:
*   `get_weather`: A standard tool that quickly returns mock weather data.
*   `slow_get_weather`: A tool that introduces a `time.sleep(5)` before returning mock weather data, simulating a slow-running operation.
*   `get_current_time`: Another standard tool.

## Streamlit App (`streamlit_app.py`)

Provides a simple web interface to:
*   Connect to the ADK server (manages session automatically).
*   Send questions to the agent.
*   Display the agent's streamed response in a chat-like format, using the same text streaming logic described above.
*   Show raw JSON events in an expandable section for debugging.

## Conclusions from Testing

The tests performed using `bug_reproduction_script.py` and `streamlit_app.py` indicate:

*   **Custom Client Viability**: Independent Python clients (both script-based and web-based via Streamlit) can successfully connect to the ADK `api_server`, parse the `/run_sse` SSE stream, and process all documented event types.
*   **Effective Partial Update Handling**: The described streaming logic effectively handles ADK's `partial:true` events, allowing for a responsive, progressive text display that mimics natural conversation flow without duplicating content.
*   **Impact of Synchronous Tool Delays**: Synchronous delays in tools (e.g., `time.sleep()`) can cause the agent to pause its output until the tool completes. The `/run_sse` stream remains open, and events resume after the delay. This underscores that while the ADK itself is asynchronous, a synchronously blocking tool will make the *overall response time for that part of the interaction* dependent on the tool's execution time. For highly responsive UIs with long-running tools, the tools themselves should be designed to be non-blocking or report progress if possible (though ADK's current tool protocol is request/response).

These findings alleviate initial concerns that ADK's streaming output might be an opaque "black box" or exclusively usable by a proprietary ADK front-end. Custom front-ends capable of rich, interactive experiences are demonstrably feasible. 