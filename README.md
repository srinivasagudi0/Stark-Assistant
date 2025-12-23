# Stark Assistant

Stark Assistant is a modular, OpenAI-powered command-line assistant designed to demonstrate clean system architecture, intent recognition, action execution, and short-term contextual memory.

The project focuses on correctness, clarity, and separation of concerns rather than feature bloat. It is built as a solid v1 foundation that can be extended into more advanced agent systems.

---

## Features

* Natural language understanding powered by OpenAI
* Intent classification: ANSWER vs ACTION
* File-based actions: read, write, append, delete
* Context-aware commands ("that file", "again", "last file")
* Short-term action memory
* Clean pipeline architecture
* Backend-only logging

---

## Example Commands

```
read main.py
write hello in notes.txt
append world
delete that file
```

---

## Running the Assistant

1. Install dependencies

```
pip install -r requirements.txt
```

2. Set your OpenAI API key (environment variable)

```
export OPENAI_API_KEY="your_api_key_here"
```

3. Run the assistant

```
python main.py
```

---

## Design Principles

* Stateless intent detection
* Deterministic action execution
* Memory used only for side-effect continuity
* No business logic inside the executor
* No conversational state leakage

---

## License

MIT License
