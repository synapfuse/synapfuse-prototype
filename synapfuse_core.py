synapfuse_core.py
===================

This module provides a minimal skeleton implementation of the core components
for the SynapFuse prototype. It includes a simple in-memory data store for
capturing and recalling user interactions (the `MemoryManager`) and a
command-line interface stub (`run_cli`) that illustrates how to connect
user input with the memory system. This is not a complete product and does
not include voice integration, persistence beyond runtime, or any actual
natural language generation; those features will be added in subsequent
iterations.

Usage examples:

>>> from synapfuse_core import MemoryManager
>>> mem = MemoryManager()
>>> mem.add_entry("Hello", "2025-08-12T10:00:00Z")
>>> mem.recall()
[{'text': 'Hello', 'timestamp': '2025-08-12T10:00:00Z'}]

The `run_cli` function can be executed directly to try out a simple
interactive loop. Note that this loop is synchronous and blocking,
making it suitable only for demonstration purposes in a terminal.
"""

from __future__ import annotations

import datetime
import json
import os
import time
from dataclasses import dataclass, field

try:
    # 'requests' is a third‑party library commonly available in modern Python environments.
    # It is used here for making HTTP requests to the ElevenLabs API when text‑to‑speech
    # functionality is enabled. If it is not installed in the runtime environment,
    # the `ImportError` will be caught and the speak function will gracefully fall back
    # to a simple print stub.
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore
from typing import List, Dict, Optional


@dataclass
class MemoryEntry:
    """Represents a single entry in the conversation memory."""

    text: str
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

    def to_dict(self) -> Dict[str, str]:
        """Return a serializable representation of the entry."""
        return {
            "text": self.text,
            "timestamp": self.timestamp.isoformat() + "Z",
        }


class MemoryManager:
    """
    In-memory storage for conversation entries.

    The MemoryManager collects entries as they occur and can return the
    most recent entries upon request. This is a simple stand-in for a
    more robust storage solution (such as a database with embeddings
    for similarity search) that might be used in a production system.
    """

    def __init__(self) -> None:
        self._entries: List[MemoryEntry] = []

    def add_entry(self, text: str, timestamp: Optional[datetime.datetime] = None) -> None:
        """Add a new entry to the memory.

        Args:
            text (str): The raw text of the user or system message.
            timestamp (datetime.datetime, optional): The time the entry was created.
                If None, uses the current UTC time.
        """
        entry = MemoryEntry(text=text, timestamp=timestamp or datetime.datetime.utcnow())
        self._entries.append(entry)

    def recall(self, n: int = 5) -> List[Dict[str, str]]:
        """Return the most recent `n` entries in reverse chronological order.

        Args:
            n (int): Number of entries to retrieve.

        Returns:
            List[Dict[str, str]]: A list of serialized entries, newest first.
        """
        return [entry.to_dict() for entry in self._entries[-n:]][::-1]

    def clear(self) -> None:
        """Clear all entries from memory."""
        self._entries.clear()


class MetricsTracker:
    """
    Collects simple latency and error metrics for prototype evaluation.

    The SynapFuse prototype needs to track the time it takes from
    receiving a user prompt to beginning the response (time-to-first-audio).
    This class collects latencies and counts requests and errors.
    """

    def __init__(self) -> None:
        self.response_latencies: List[float] = []
        self.request_count: int = 0
        self.error_count: int = 0

    def record_response(self, latency: float, error: bool = False) -> None:
        """
        Record the latency of a response and whether an error occurred.

        Args:
            latency (float): The measured latency in seconds.
            error (bool): True if the response resulted in an error.
        """
        self.response_latencies.append(latency)
        self.request_count += 1
        if error:
            self.error_count += 1

    def get_metrics(self) -> Dict[str, float]:
        """
        Compute basic metrics for the collected response latencies.

        Returns:
            Dict[str, float]: A dictionary with p50 latency, total requests,
            and total errors.
        """
        if not self.response_latencies:
            return {"p50": 0.0, "requests": 0, "errors": 0}
        sorted_latencies = sorted(self.response_latencies)
        mid = len(sorted_latencies) // 2
        p50 = sorted_latencies[mid] if len(sorted_latencies) % 2 == 1 else (
            sorted_latencies[mid - 1] + sorted_latencies[mid]) / 2
        return {
            "p50": p50,
            "requests": self.request_count,
            "errors": self.error_count,
        }



def speak(text: str) -> None:
    """
    Convert text to speech using the ElevenLabs API if configured.

    By default this function prints the text to the console. If an
    environment variable named ``ELEVENLABS_API_KEY`` is set and the
    ``requests`` library is available, the text will be sent to the
    ElevenLabs text‑to‑speech endpoint using the voice configured via
    ``ELEVENLABS_VOICE_ID`` (defaulting to the Rachel voice). The
    resulting audio is written to a file named ``output.mp3`` in the
    current working directory. This simple implementation does not
    stream audio; it merely downloads the complete result and prints a
    message indicating where the file was saved.

    Args:
        text (str): The text to speak aloud.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    # Default voice ID for ElevenLabs' Rachel voice. Users can override this by
    # setting ELEVENLABS_VOICE_ID in their environment. See the ElevenLabs
    # documentation for a list of available voices.
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    if api_key and requests:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.75,
                "similarity_boost": 0.75,
            },
        }
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                out_path = "output.mp3"
                with open(out_path, "wb") as audio_file:
                    audio_file.write(response.content)
                print(f"(audio saved to {out_path})")
                return
            else:
                print(
                    f"(tts error) ElevenLabs API returned status {response.status_code}: {response.text}"
                )
         print(f"(speaking) {text}")



def require_password() -> None:
    """
    Prompt the user for a password before allowing access to the CLI.

    The expected password is read from the environment variable
    `PROTOTYPE_PASSWORD`. If not set, a default password of "2ndMind"
    is used. The user has three attempts to enter the correct password.
    If all attempts fail, the program exits.
    """
    # Use the provided default password for the prototype. If an
    # environment variable PROTOTYPE_PASSWORD is set, it will override
    # this value. Otherwise, the system will default to the password
    # specified below. This is a shared access code for all early testers.
    expected = os.getenv("PROTOTYPE_PASSWORD", "2ndMind")
    for attempt in range(3):
        entered = input("Enter password: ")
        if entered == expected:
            return
        print("Incorrect password. Try again.")
    print("Failed authentication. Exiting.")
    raise SystemExit(1)


class PersistentMemoryManager(MemoryManager):
    """
    A memory manager that persists entries to a JSON file. This class
    extends the basic MemoryManager to automatically load existing
    conversation history from a file at initialization and save any
    changes back to the file. If the file does not exist, it will
    be created on the first write.

    Args:
        filepath (str): Path to the JSON file for persistence. Defaults
            to "memory_store.json" in the current working directory.
    """

    def __init__(self, filepath: str = "memory_store.json") -> None:
        # Initialise base memory manager without entries
        super().__init__()
        self.filepath = filepath
        self._load_entries()

    def _load_entries(self) -> None:
        """Load entries from the persistence file if it exists."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Ensure loaded data is a list of dicts
                for entry_data in data:
                    # Handle timestamps formatted with trailing 'Z'
                    ts_str = entry_data.get("timestamp", "")
                    # Remove trailing 'Z' and parse
                    ts_clean = ts_str[:-1] if ts_str.endswith("Z") else ts_str
                    try:
                        timestamp = datetime.datetime.fromisoformat(ts_clean)
                    except ValueError:
                        timestamp = datetime.datetime.utcnow()
                    text = entry_data.get("text", "")
                    self._entries.append(MemoryEntry(text=text, timestamp=timestamp))
            except (json.JSONDecodeError, OSError):
                # If there's an error loading, start fresh
                self._entries = []

    def _save_entries(self) -> None:
        """Write all entries to the persistence file in JSON format."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump([entry.to_dict() for entry in self._entries], f, indent=2)
        except OSError:
            # In case of error, ignore to avoid crashing
            pass

    def add_entry(self, text: str, timestamp: Optional[datetime.datetime] = None) -> None:
        """Add a new entry and persist the updated memory to disk."""
        super().add_entry(text, timestamp)
        self._save_entries()

    def clear(self) -> None:
        """Clear all entries and persist the change."""
        super().clear()
        self._save_entries()



def run_cli_persistent(filepath: str = "memory_store.json") -> None:
    """
    Run a command-line interface using a persistent memory manager.

    This CLI behaves like `run_cli`, but stores conversation history
    across sessions in a JSON file specified by `filepath`.

    Args:
        filepath (str): Path to the persistence JSON file.
    """
    # Enforce password gate
    require_password()
    mem = PersistentMemoryManager(filepath=filepath)
    metrics = MetricsTracker()
    short_mode = False
    print(
        "SynapFuse CLI (persistent) – type '/exit' to quit, '/recall n' to recall, '/clear' to clear memory,\n"
        "'/metrics' to view metrics, '/short' to toggle short reply mode."
    )
    while True:
        user_input = input("User> ")
        if not user_input:
            continue
        command, *args = user_input.strip().split()
        if command == "/exit":
            print("Exiting...")
            break
        elif command == "/clear":
            mem.clear()
            print("Memory cleared.")
            continue
        elif command == "/recall":
            try:
                count = int(args[0]) if args else 5
            except ValueError:
                print("Invalid number. Using default of 5.")
                count = 5
            entries = mem.recall(count)
            if not entries:
                print("No entries in memory.")
            else:
                for idx, entry in enumerate(entries, 1):
                    print(f"{idx}. {entry['timestamp']}: {entry['text']}")
            continue
        elif command == "/short":
            short_mode = not short_mode
            print(f"Short mode {'enabled' if short_mode else 'disabled'}.")
            continue
        elif command == "/metrics":
            m = metrics.get_metrics()
            print(
                f"Metrics – p50 latency: {m['p50']:.3f}s, total requests: {m['requests']}, errors: {m['errors']}"
            )
            continue
        else:
            start_time = time.monotonic()
            try:
                mem.add_entry(user_input)
                response = generate_response(user_input)
                if short_mode:
                    max_len = 60
                    if len(response) > max_len:
                        response = response[:max_len] + "..."
                latency = time.monotonic() - start_time
                metrics.record_response(latency)
                speak(response)
                print(f"Assistant> {response}")
            except Exception:
                latency = time.monotonic() - start_time
                metrics.record_response(latency, error=True)
                print("Assistant> [Error generating response]")



def generate_response(prompt: str) -> str:
    """
    Generate a stub response for a given user prompt.

    In the real system this would call a language model or other
    processing pipeline. Here we simply echo the prompt to
    demonstrate the flow.

    Args:
        prompt (str): The user's input.

    Returns:
        str: A placeholder response.
    """
    return f"[Stub response to '{prompt}']"



def run_cli() -> None:
    """
    Run a simple command-line interface to interact with the memory manager.

    Commands:
        /recall [n]   - Show the most recent `n` entries (default 5).
        /clear        - Clear the memory.
        /exit         - Exit the CLI.

    Any other input is treated as a new entry; the system will respond
    with a stubbed message and store the entry in memory.
    """
    # Enforce password gate before starting
    require_password()
    mem = MemoryManager()
    metrics = MetricsTracker()
    short_mode = False
    print(
        "SynapFuse CLI – type '/exit' to quit, '/recall n' to recall, '/clear' to clear memory, '\n"
        "'/metrics' to view metrics, '/short' to toggle short reply mode."
    )
    while True:
        user_input = input("User> ")
        if not user_input:
            continue
        command, *args = user_input.strip().split()
        if command == "/exit":
            print("Exiting...")
            break
        elif command == "/clear":
            mem.clear()
            print("Memory cleared.")
            continue
        elif command == "/recall":
            # parse optional numeric argument
            try:
                count = int(args[0]) if args else 5
            except ValueError:
                print("Invalid number. Using default of 5.")
                count = 5
            entries = mem.recall(count)
            if not entries:
                print("No entries in memory.")
            else:
                for idx, entry in enumerate(entries, 1):
                    print(f"{idx}. {entry['timestamp']}: {entry['text']}")
            continue
        elif command == "/short":
            # Toggle short reply mode
            short_mode = not short_mode
            print(f"Short mode {'enabled' if short_mode else 'disabled'}.")
            continue
        elif command == "/metrics":
            # Show current metrics
            m = metrics.get_metrics()
            print(
                f"Metrics – p50 latency: {m['p50']:.3f}s, total requests: {m['requests']}, errors: {m['errors']}"
            )
            continue
        else:
            # treat as regular user input
            start_time = time.monotonic()
            try:
                mem.add_entry(user_input)
                response = generate_response(user_input)
                # Apply short mode if active
                if short_mode:
                    max_len = 60
                    if len(response) > max_len:
                        response = response[:max_len] + "..."
                latency = time.monotonic() - start_time
                metrics.record_response(latency)
                # Speak the response (stub)
                speak(response)
                print(f"Assistant> {response}")
            except Exception:
                latency = time.monotonic() - start_time
                metrics.record_response(latency, error=True)
                print("Assistant> [Error generating response]")
   except Exception:
    latency = time.monotonic() - start_time
    metrics.record_response(latency, error=True)
    print("Assistant> [Error generating response]")

if __name__ == "__main__":
    # Only run the CLI if executed as a script.
    run_cli()

            print(f"(tts error) Exception during ElevenLabs request: {e}")
    # Fallback: no API key or requests library available. Print the text.
    print(f"(speaking) {text}")
