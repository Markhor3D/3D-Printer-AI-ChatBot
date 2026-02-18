# 3D Printer ChatBot

An asynchronous, AI-powered hardware controller that connects Google's Gemini LLM to a Markhor3D Enabler 3D printer using Pronterface/Printrun. 

## Features
* **Smart Hardware Handshake:** Automatically retrieves firmware info and active baud rates upon connection (`M115`).
* **AI Diagnostics:** Troubleshoots hardware faults by actively checking temperature pulses (`M105`) and limit switch endstops (`M119`).
* **Safe Homing Protocol:** Injects a protective 5mm Z-hop before executing standard `G28` homing to prevent bed scratching.
* **Asynchronous Queueing:** Uses Python's `asyncio` to safely pass multi-line G-code responses from the hardware terminal directly to the AI's context window.

## Setup & Installation
1. Clone this repository to your local machine.
2. Create a virtual environment: `python -m venv .venv`
3. Activate the environment and install dependencies:
   `pip install google-genai python-dotenv`
   *(Note: Ensure you have the Printrun 2.2.0 source code in your directory).*
4. Create a `.env` file in the root directory and add your API key:
   `GEMINI_API_KEY=your_key_here`

## Usage
1. Launch the UI by navigating to the Printrun directory and running `python pronterface.py`.
2. Connect to your printer via the GUI.
3. Use the terminal chat to talk to your AI Co-Pilot! Try asking: *"Run a full diagnostic check"* or *"Home all axes."*