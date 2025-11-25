import asyncio
import json
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
import msvcrt


agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(
        credential=AzureCliCredential(),
        endpoint=os.environ["AOAI_ENDPOINT"],
        deployment_name=os.environ["AOAI_DEPLOYMENT"],
    ),
    name="Assistant",
    instructions="You are a helpful assistant.",
)

PERSIST_DIR = Path(__file__).parent / "persisted_threads"
PERSIST_DIR.mkdir(exist_ok=True)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "conversation"


def _thread_path(name: str) -> Path:
    return PERSIST_DIR / f"{_slugify(name)}.json"


def open_persist_directory() -> None:
    print(f"Persisted threads directory: {PERSIST_DIR}")
    try:
        os.startfile(PERSIST_DIR)  # type: ignore[attr-defined]
        print("Opened folder in File Explorer.\n")
    except Exception as exc:  # pragma: no cover - best-effort helper
        print(f"Could not open folder automatically ({exc}). Open it manually if needed.\n")


def clear_console() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def render_layout(active_label: str, dirty: bool, conversation_log: list[Tuple[str, str]]) -> None:
    clear_console()
    term_width = shutil.get_terminal_size(fallback=(100, 20)).columns
    width = max(60, min(term_width, 120))
    title_border = "=" * width
    menu_border = "-" * width
    title = "Lab 10: Interactive Persistence"

    print(title_border)
    print(title.center(width))
    print(title_border)

    menu_lines = [
        "Hotkeys: F2=New  F4=Load  F10=Save  F12=Open folder",
    ]
    for line in menu_lines:
        print(line.center(width))

    print(menu_border)
    thread_label = active_label if active_label != "unsaved" else "UNNAMED"
    if dirty:
        thread_label += " *"
    print(f"Thread: {thread_label}".center(width))
    print(menu_border)
    print()

    if conversation_log:
        print("Conversation so far:\n")
        for user_msg, assistant_msg in conversation_log:
            print(f"USER: {user_msg}")
            print(f"ASSISTANT: {assistant_msg}\n")
    else:
        print("Type a prompt and press Enter to talk to the assistant. Type 'exit' to quit.\n")


async def save_thread(thread, name: str) -> Path:
    state = await thread.serialize()
    path = _thread_path(name)
    path.write_text(json.dumps(state, indent=2))
    return path


async def load_thread(name: str):
    path = _thread_path(name)
    data = json.loads(path.read_text())
    return await agent.deserialize_thread(data)


async def load_existing_thread() -> tuple[Optional[object], Optional[str]]:
    files = sorted(PERSIST_DIR.glob("*.json"))
    if not files:
        print("No saved threads found yet. Press F10 to persist one.\n")
        return None, None

    print("Saved threads:")
    for path in files:
        print(f"- {path.stem}")

    choice = input("Enter the saved name to load (or leave blank to cancel): ").strip()
    if not choice:
        print("Load cancelled.\n")
        return None, None
    try:
        thread = await load_thread(choice)
    except FileNotFoundError:
        print("Thread not found. Make sure you typed the saved name exactly.\n")
        return None, None
    print(f"Loaded thread '{_slugify(choice)}'.\n")
    return thread, _slugify(choice)


def _read_input_with_hotkeys(prompt_label: str = "USER> ") -> Tuple[Optional[str], Optional[str]]:
    buffer: list[str] = []
    print(prompt_label, end="", flush=True)
    while True:
        ch = msvcrt.getwch()
        if ch in {"\r", "\n"}:
            print()
            text = "".join(buffer).strip()
            return text, None
        if ch == "\x08":
            if buffer:
                buffer.pop()
                print("\b \b", end="", flush=True)
            continue
        if ch in {"\x00", "\xe0"}:  # function key prefix
            key_code = ord(msvcrt.getwch())
            mapping = {
                60: "new",          # F2
                62: "load",         # F4
                68: "save",         # F10
                134: "open_folder",  # F12
            }
            command = mapping.get(key_code)
            if command:
                print()
                return None, command
            continue
        buffer.append(ch)
        print(ch, end="", flush=True)


async def send_prompt(thread, prompt: str) -> tuple[object, str]:
    result = await agent.run(prompt, thread=thread)
    return thread, result.text


async def save_current_thread(thread, active_label: str) -> Tuple[Optional[str], bool]:
    if thread is None:
        print("No active thread to save.\n")
        return None, True
    name = active_label
    if name == "unsaved":
        name = input("Friendly name to save as: ").strip()
        if not name:
            print("A thread name is required to save it.\n")
            return None, True
    else:
        print(f"Overwriting existing thread '{name}'.")
    path = await save_thread(thread, name)
    slug = path.stem
    print(f"Thread saved as '{slug}'.\n")
    return slug, False


async def handle_new_thread(active_thread, active_label: str, dirty: bool):
    if dirty:
        choice = input("Save the current thread before starting a new one? (y/N): ").strip().lower()
        if choice in {"y", "yes"}:
            saved_name, dirty = await save_current_thread(active_thread, active_label)
            if saved_name:
                active_label = saved_name
    active_thread = agent.get_new_thread()
    print("Started a fresh thread.\n")
    return active_thread, "unsaved", False


async def menu_loop() -> None:
    active_thread = agent.get_new_thread()
    active_label = "unsaved"
    dirty = False
    conversation_log: list[Tuple[str, str]] = []

    while True:
        render_layout(active_label, dirty, conversation_log)
        prompt, command = _read_input_with_hotkeys()

        if command == "save":
            saved_name, dirty = await save_current_thread(active_thread, active_label)
            if saved_name:
                active_label = saved_name
            continue
        if command == "new":
            active_thread, active_label, dirty = await handle_new_thread(active_thread, active_label, dirty)
            conversation_log.clear()
            continue
        if command == "load":
            loaded_thread, loaded_name = await load_existing_thread()
            if loaded_thread:
                active_thread = loaded_thread
                active_label = loaded_name or "unsaved"
                dirty = False
                conversation_log.clear()
            continue
        if command == "open_folder":
            open_persist_directory()
            continue

        if not prompt:
            print("(Empty prompt) Use the function keys or type a message.\n")
            continue
        if prompt.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        active_thread, response_text = await send_prompt(active_thread, prompt)
        conversation_log.append((prompt, response_text))
        print(f"\nASSISTANT> {response_text}\n")
        dirty = True


if __name__ == "__main__":
    asyncio.run(menu_loop())