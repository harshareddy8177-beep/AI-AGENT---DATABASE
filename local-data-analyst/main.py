import io
import importlib.util
import json
from pathlib import Path

import ollama
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

MODEL = "qwen2.5:3b"
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

analysis_path = BASE_DIR / "analysis.py"
analysis_spec = importlib.util.spec_from_file_location(
    "local_analysis",
    analysis_path,
)
if analysis_spec is None or analysis_spec.loader is None:
    raise RuntimeError(f"Could not load analysis helpers from {analysis_path}")

analysis_module = importlib.util.module_from_spec(analysis_spec)
analysis_spec.loader.exec_module(analysis_module)
get_missing_values = analysis_module.get_missing_values
get_profile = analysis_module.get_profile
group_and_aggregate = analysis_module.group_and_aggregate
summarize_column = analysis_module.summarize_column

app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)

# Demo storage: uploaded data and chats remain in memory while the server runs.
datasets = {}
conversations = {}

SYSTEM_MESSAGE = {
    "role": "system",
    "content": (
        "You are a local data analytics assistant. Answer questions using "
        "the uploaded dataset and the available analysis tools. Use a tool "
        "for dataset facts or calculations. Never invent numbers. If a "
        "requested column is not present, explain that to the user."
    ),
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dataset_profile",
            "description": "Get the dataset's size, columns, types, and missing values.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_column",
            "description": "Summarize a column's statistics or most common values.",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {
                        "type": "string",
                        "description": "The dataset column to summarize",
                    }
                },
                "required": ["column"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_missing_values",
            "description": "Get the number of missing values in every column.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "group_and_aggregate",
            "description": "Group rows and calculate a sum, mean, count, min, or max.",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_column": {
                        "type": "string",
                        "description": "Column to group by",
                    },
                    "value_column": {
                        "type": "string",
                        "description": "Column to aggregate",
                    },
                    "aggregation": {
                        "type": "string",
                        "enum": ["sum", "mean", "count", "min", "max"],
                    },
                },
                "required": [
                    "group_column",
                    "value_column",
                    "aggregation",
                ],
            },
        },
    },
]


class ChatRequest(BaseModel):
    session_id: str
    message: str


def run_tool(tool_name, arguments, df):
    """Run only the tools explicitly allowed above."""
    if tool_name == "get_dataset_profile":
        return json.dumps(get_profile(df))

    if tool_name == "summarize_column":
        return summarize_column(df, arguments["column"])

    if tool_name == "get_missing_values":
        return get_missing_values(df)

    if tool_name == "group_and_aggregate":
        return group_and_aggregate(
            df,
            arguments["group_column"],
            arguments["value_column"],
            arguments["aggregation"],
        )

    return "That tool is not available."


def run_agent(session_id, user_message, df):
    if session_id not in conversations:
        conversations[session_id] = [SYSTEM_MESSAGE.copy()]

    messages = conversations[session_id]
    messages.append({"role": "user", "content": user_message})

    # Allow a few tool calls, then return the model's answer.
    for _ in range(5):
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )

        assistant_message = response.message
        messages.append(assistant_message)

        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            return assistant_message.content or "I couldn't produce an answer."

        for call in tool_calls:
            result = run_tool(
                call.function.name,
                call.function.arguments,
                df,
            )

            messages.append({
                "role": "tool",
                "name": call.function.name,
                "content": str(result),
            })

    return "I reached the tool-call limit for this request."


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/upload")
async def upload_csv(
    session_id: str = Form(...),
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    contents = await file.read()

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="For this demo, CSV files must be under 10 MB.",
        )

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the CSV: {error}",
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="The CSV file has no data rows.",
        )

    datasets[session_id] = df
    conversations.pop(session_id, None)

    return get_profile(df)


@app.post("/chat")
def chat(request: ChatRequest):
    df = datasets.get(request.session_id)

    if df is None:
        raise HTTPException(
            status_code=400,
            detail="Upload a CSV file before asking questions.",
        )

    try:
        reply = run_agent(request.session_id, request.message, df)
        return {"reply": reply}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail=(
                "Couldn't connect to Ollama. Check that Ollama is running "
                "and the model has been downloaded."
            ),
        )


@app.post("/reset")
def reset(request: ChatRequest):
    conversations.pop(request.session_id, None)
    return {"ok": True}