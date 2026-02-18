import os
import dotenv
import google.genai as genai
from google.adk.agents.llm_agent import Agent
from printrun_wrapper import PrintrunClient

# Load environment variables from .env file
dotenv.load_dotenv()

# Configure the generative AI client with the API key


# Initialize the PrintrunClient
printrun_client = PrintrunClient()

# Define the tools

def connect_printer(port: str, baud_rate: int) -> str:
    """
    Connects to the 3D printer.

    Args:
        port: The serial port (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux).
        baud_rate: The baud rate for the connection (e.g., 115200).

    Returns:    
        A status message indicating success or failure.
    """
    return printrun_client.connect_printer(port, baud_rate)


def disconnect_printer() -> str:
    """
    Disconnects from the 3D printer.

    Returns:
        A status message.
    """
    return printrun_client.disconnect_printer()

def get_hardware_info() -> str:
    """
    Retrieves the printer's firmware version, machine type, and hardware capabilities.
    Returns a string containing the printer's hardware report.
    """
    return printrun_client.get_hardware_info()

def run_diagnostics() -> str:
    """
    Runs a hardware diagnostic check on the printer, returning current temperatures and endstop limit switch states.
    Use this when the user asks to check the printer's health, troubleshoot movement issues, or perform a diagnostic.
    """
    return printrun_client.run_diagnostics()

def get_printer_status() -> str:
    """
    Checks the connection status of the printer.

    Returns:
        A string indicating the printer's status (online, offline, printing, paused).
    """
    return printrun_client.get_printer_status()


def send_raw_gcode(command: str) -> str:
    """
    Sends a raw G-code command directly to the printer.

    Args:
        command: The G-code command string (e.g., "M105").

    Returns:
        A status message indicating success or failure.
    """
    return printrun_client.send_raw_gcode(command)


def load_gcode_file(filepath: str) -> str:
    """
    Loads a G-code file for printing. This does not start the print.

    Args:
        filepath: The path to the G-code file.

    Returns:
        A status message.
    """
    return printrun_client.load_gcode_file(filepath)


def start_print() -> str:
    """
    Starts the printing process for the currently loaded G-code.

    Returns:
        A status message.
    """
    return printrun_client.start_print()


def pause_print() -> str:
    """
    Pauses an active print job.

    Returns:
        A status message.
    """
    return printrun_client.pause_print()


def resume_print() -> str:
    """
    Resumes a paused print job.

    Returns:
        A status message.
    """
    return printrun_client.resume_print()


def cancel_print() -> str:
    """
    Aborts the current print job.

    Returns:
        A status message.
    """
    return printrun_client.cancel_print()


def get_print_progress() -> str:
    """
    Retrieves the status of the current print.

    Returns:
        A string with print progress information.
    """
    return printrun_client.get_print_progress()


def set_temperatures(tool_temp: int = None, bed_temp: int = None) -> str:
    """
    Sets target temperatures for the hotend and/or heated bed.

    Args:
        tool_temp: Target temperature for the hotend (e.g., 200).
        bed_temp: Target temperature for the heated bed (e.g., 60).

    Returns:
        A status message.
    """
    return printrun_client.set_temperatures(tool_temp, bed_temp)


def get_temperatures() -> str:
    """
    Reads the current temperatures of the hotend and heated bed.

    Returns:
        A string with current temperature readings.
    """
    return printrun_client.get_temperatures()


def move_printhead(x: float = None, y: float = None, z: float = None, speed: int = None) -> str:
    """
    Moves the printhead to a specified absolute position.

    Args:
        x: X-coordinate.
        y: Y-coordinate.
        z: Z-coordinate.
        speed: Feed rate (mm/min).

    Returns:
        A status message.
    """
    return printrun_client.move_printhead(x, y, z, speed)


def home_axes(axes: str = "XYZ") -> str:
    """
    Homes one or more printer axes.

    Args:
        axes: A string representing the axes to home (e.g., "X", "Y", "Z", "XY", "XYZ").

    Returns:
        A status message.
    """
    return printrun_client.home_axes(axes)


def extrude_filament(amount: float, speed: int = None, retract: bool = False) -> str:
    """
    Extrudes or retracts filament.

    Args:
        amount: The amount of filament to extrude/retract in mm.
        speed: The feed rate for extrusion/retraction in mm/min.
        retract: If True, retracts filament. Otherwise, extrudes.

    Returns:
        A status message.
    """
    return printrun_client.extrude_filament(amount, speed, retract)


def list_sd_files() -> str:
    """
    Lists files on the printer's SD card. (Requires printer support for M20)

    Returns:
        A string with a list of files or an error message.
    """
    return printrun_client.list_sd_files()


def upload_to_sd(local_filepath: str, remote_filename: str = None) -> str:
    """
    Uploads a G-code file to the printer's SD card.
    Note: Printcore's direct SD upload capability is limited; this would typically
    require a more involved transfer protocol or external tool integration.
    This is a placeholder and might require a different approach depending on printer firmware.

    Args:
        local_filepath: Path to the local G-code file.
        remote_filename: Desired filename on the SD card. If None, uses local filename.

    Returns:
        A status message.
    """
    return printrun_client.upload_to_sd(local_filepath, remote_filename)


def print_from_sd(filename: str) -> str:
    """
    Starts a print from a G-code file on the SD card. (Requires printer support for M23/M24)

    Args:
        filename: The name of the G-code file on the SD card.

    Returns:
        A status message.
    """
    return printrun_client.print_from_sd(filename)


# A more descriptive name for the agent
name = 'Printer_Control_Agent'

# A more descriptive description for the agent
description = 'An_intelligent_assistant_that_can_control_a_3D_printer_using_Printrun_functionalities.'

# A more specific instruction for the agent
instruction = """
You are a 3D Printer Control Agent. Your primary role is to manage and control a 3D printer
using a set of specialized tools. You can connect to printers, load G-code files,
start/pause/resume/cancel prints, monitor status, move the printhead, set temperatures,
extrude filament, interact with the printer's SD card, and run hardware diagnostics.

When asked to perform an action, use the appropriate tool. For example, if the user asks
to connect to a printer, use the `connect_printer` tool. If the user asks to start a print,
use the `start_print` tool. If the user asks to check the printer's health, troubleshoot, or run diagnostics, use the `run_diagnostics` tool.

Whenever you successfully connect to a printer, you MUST immediately use the `get_hardware_info` tool.

Always confirm with the user before executing any action that might move the printer head or start a print.
Provide clear and concise responses based on the output of the tools.
"""

# A list of tools that the agent can use
tools = [
    connect_printer,
    disconnect_printer,
    get_printer_status,
    get_hardware_info,
    run_diagnostics,
    send_raw_gcode,
    load_gcode_file,
    start_print,
    pause_print,
    resume_print,
    cancel_print,
    get_print_progress,
    set_temperatures,
    get_temperatures,
    move_printhead,
    home_axes,
    extrude_filament,
    list_sd_files,
    upload_to_sd,
    print_from_sd
]

# The model to use for the agent
model = 'gemini-3-flash-preview'

# Create the agent
root_agent = Agent(
    name=name,
    description=description,
    instruction=instruction,
    tools=tools,
    model=model,
)

# Start a terminal chat loop
if __name__ == "__main__":
    import asyncio
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    import uuid
    
    async def terminal_chat():
        # 1. Initialize Runner
        runner = InMemoryRunner(
            agent=root_agent,
            app_name="PrinterControlApp"
        )
        session_id = str(uuid.uuid4())
        user_id = "local_user"
        
        # 2. Safely create the session natively inside the async loop
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id
        )
        
        print(f"Starting {name}...")
        print("Type 'exit' or 'quit' to end the session.\n")
        
        while True:
            # 3. Use to_thread so the input prompt doesn't freeze the async engine
            user_input = await asyncio.to_thread(input, "You: ")
            user_input = user_input.strip()
            
            if user_input.lower() in ['exit', 'quit']:
                print("Shutting down agent...")
                break
                
            if not user_input:
                continue
                
            try:
                message_content = types.Content(
                    role='user', 
                    parts=[types.Part.from_text(text=user_input)]
                )
                
                # 4. Use run_async() to stay inside the same event loop
                async for event in runner.run_async(
                    user_id=user_id, 
                    session_id=session_id, 
                    new_message=message_content
                ):
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            # Safely check if the agent is using a tool
                            if getattr(part, 'function_call', None):
                                print(f"🔧 [Agent is using tool: {part.function_call.name}]")
                            
                            # Safely capture any text the agent speaks
                            elif getattr(part, 'text', None):
                                if part.text.strip():
                                    print(f"Agent: {part.text}")
                                    
            except Exception as e:
                print(f"An error occurred: {e}")

    # 5. Execute the entire chat natively in one event loop
    asyncio.run(terminal_chat())