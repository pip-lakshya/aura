# AURA — Adaptive Unified Retrieval Assistant

> **AURA: A Voice-Powered Personal Memory & Knowledge Retrieval System**
>
> *"Your second brain — remember everything, retrieve anything."*

![AURA Interface](assets/interface.png)

---

# Overview

AURA (Adaptive Unified Retrieval Assistant) is an AI-powered desktop assistant designed to act as a personal memory system.

Unlike traditional chatbots that forget conversations, AURA captures, organizes, and retrieves information from your personal knowledge base using natural language, voice commands, and AI-powered semantic understanding.

AURA combines:

* AI Memory Management
* Voice Interaction
* Knowledge Graphs
* Local Database Storage
* Intelligent Retrieval
* Interactive HUD Interface

into a single futuristic desktop application inspired by J.A.R.V.I.S from Iron Man.

---

# Key Features

## Voice-Powered Memory Capture

Speak naturally.

AURA can:

* Listen to voice input
* Convert speech to text
* Understand context
* Store memories automatically

Examples:

```text
I have my Data Engineering internship presentation next Monday.

Remember that I need to submit my project report before Friday.

My Groq API key issue was fixed today.
```

---

## Intelligent Memory Retrieval

Ask questions naturally.

Examples:

```text
Tell me about my internship.

What was I working on last week?

Show memories related to SQL.

What project did I discuss yesterday?
```

AURA searches stored memories and generates contextual answers using AI.

---

## Knowledge Graph Generation

Every memory is analyzed and converted into structured relationships.

Example:

```text
You worked on API refactoring during internship.
```

Extracted as:

```text
You
 └── worked_on
      └── API Refactoring
```

These relationships are visualized in the Cognitive Personality Graph.

---

## AI Memory Tagging

Each memory is automatically classified:

```json
{
  "topic": "Internship",
  "category": "Work",
  "emotion": "Focused",
  "importance": 8,
  "tags": [
    "internship",
    "api",
    "backend"
  ]
}
```

---

## Cognitive Personality Graph

AURA continuously builds a knowledge graph from your memories.

Tracks:

* Projects
* People
* Ideas
* Technologies
* Goals
* Relationships

Interactive graph supports:

* Dragging nodes
* Real-time layout physics
* Dynamic relationship visualization

---

## Conversation Memory

AURA remembers recent conversations.

Example:

```text
User:
Tell me about my internship.

AURA:
You worked on API validation and Flask integration.

User:
Tell me more.

AURA:
You also discussed scheduling, debugging, and deployment.
```

---

## AI Assistant Personality

AURA uses a loyal assistant personality.

Responses are designed to feel like:

```text
Systems online, Boss.

I found 5 relevant memories related to your internship.
```

Inspired by:

* J.A.R.V.I.S.
* Friday
* Personal Digital Twin systems

---

## Text-to-Speech Responses

AURA speaks responses aloud using:

```text
edge-tts
```

Features:

* Natural sounding voice
* Real-time playback
* Mute support
* Audio visualization

---

## Real-Time Audio Monitoring

AURA monitors:

### Microphone Input

Displays:

```text
MIC IN
```

with live amplitude meter.

### System Output

Displays:

```text
SYS OUT
```

with live speech playback levels.

---

# Architecture

```text
User
 │
 ▼
Voice Input
 │
 ▼
Speech Recognition
 │
 ▼
Groq Whisper STT
 │
 ▼
AURA Brain
 │
 ▼
Groq LLM
 │
 ├── Memory Tagging
 │
 ├── Relationship Extraction
 │
 └── Query Resolution
 │
 ▼
SQLite Database
 │
 ├── Memories
 ├── Tags
 ├── Retrieval Logs
 └── Knowledge Triples
 │
 ▼
PyQt6 HUD Interface
```

---

# Technology Stack

## Backend

* Python 3.12
* Flask
* Flask-CORS
* SQLite

---

## AI Layer

* Groq API
* Llama 3.3 70B Versatile
* Whisper Large

---

## Voice Layer

* SpeechRecognition
* PyAudio
* edge-tts
* pygame

---

## Interface

* PyQt6
* QPainter
* Custom HUD Components

---

## Visualization

* Force Directed Graph
* Real-Time Physics Simulation

---

# Database Design

## Memories

Stores:

```text
memory_id
content
timestamp
topic
category
emotion
importance
```

---

## Tags

Stores:

```text
tag_id
tag_name
```

---

## Memory Tags

Many-to-many relationship:

```text
memory_id
tag_id
```

---

## Retrieval Logs

Stores:

```text
query
timestamp
results
```

Used for analytics.

---

## Knowledge Triples

Stores:

```text
source
relation
target
memory_id
timestamp
```

Example:

```text
You
 └── learned
      └── Flask
```

---

# Project Structure

```text
AURA/
│
├── assets/
│   ├── logo.png
│   └── logo.ico
│
├── ai_brain.py
├── config.py
├── database.py
├── main.py
├── server.py
├── seed_memories.py
├── ui.py
├── voice.py
│
├── requirements.txt
├── .env.example
├── README.md
│
└── aura_memory.db
```

---

# Installation

Clone repository:

```bash
git clone https://github.com/yourusername/AURA.git
cd AURA
```

Create virtual environment:

```bash
python -m venv venv
```

Activate:

### Windows

```bash
venv\Scripts\activate
```

### Linux

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create:

```text
.env
```

Example:

```env
GROQ_API_KEY=YOUR_API_KEY

AURA_INPUT_DEVICE=9
AURA_SAMPLE_RATE=48000

AURA_SILENCE_THRESHOLD=0.0015
AURA_WAKE_CHUNK_SECONDS=1.4
AURA_WAKE_COOLDOWN_SECONDS=1.2
```

---

# Running AURA

```bash
python main.py
```

---

# Build Desktop Application

```bash
pyinstaller --onedir --windowed --name AURA main.py
```

With icon:

```bash
pyinstaller --onedir --windowed --icon=assets/logo.ico --name AURA main.py
```

---

# Use Cases

### Students

Remember:

* Assignments
* Notes
* Exams
* Projects

---

### Developers

Track:

* Bugs
* Decisions
* Architecture
* Research

---

### Researchers

Maintain:

* Knowledge Base
* Citations
* Findings
* Experiments

---

### Personal Productivity

Store:

* Goals
* Ideas
* Meetings
* Reflections

---

# Why AURA?

Most assistants answer questions.

AURA remembers.

Most note-taking apps store information.

AURA understands relationships.

Most chatbots forget.

AURA builds a living knowledge graph of your life, projects, and ideas.

---

# Author

**Lakshya Bhandari**

B.Tech CSE (Data Science)
SKIT, Jaipur

**AURA — Adaptive Unified Retrieval Assistant**

*"Your memories. Organized. Searchable. Alive."* 🚀
