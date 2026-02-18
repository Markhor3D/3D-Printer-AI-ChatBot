import time
import threading
from printrun.printcore import printcore
from printrun import gcoder
from queue import Queue, Empty

class PrintrunClient:
    def __init__(self):
        self.p = None # printcore instance
        self.log_queue = Queue() # To capture logs/errors from printcore
        self.is_gui_managed = False # Track if Pronterface is managing the connection

    def init_parent(self, parent_instance):
        """
        Grabs the existing printcore instance from the Pronterface GUI
        and safely hooks into the terminal output so the AI can 'hear' the printer.
        """
        if hasattr(parent_instance, 'p'):
            self.p = parent_instance.p
            self.is_gui_managed = True
            
            # Safely hook into Printrun 2.2.0's receive callback (recvcb)
            # This allows the AI to read the terminal without breaking the GUI
            if hasattr(self.p, 'recvcb'):
                original_recvcb = self.p.recvcb
                def shared_recvcb(line):
                    self.log_queue.put(line)
                    if original_recvcb:
                        original_recvcb(line)
                self.p.recvcb = shared_recvcb

    def _log_callback(self, message):
        """Callback to capture printcore logs."""
        self.log_queue.put(message)

    def connect_printer(self, port, baud_rate):
        """Commands the printer engine to connect directly."""
        try:
            # We don't care if the GUI is managed or not, just connect!
            self.p.connect(port, baud_rate)
            return f"Successfully initiated connection to {port} at {baud_rate} baud."
        except Exception as e:
            return f"Failed to connect: {e}"

    def get_hardware_info(self) -> str:
        """Requests firmware and hardware info from the printer using M115, and appends connection settings."""
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        
        # 1. Grab the active connection details directly from Pronterface's engine
        current_port = getattr(self.p, 'port', 'Unknown Port')
        current_baud = getattr(self.p, 'baud', 'Unknown Baud')
        connection_header = f"=== CONNECTION INFO ===\nPort: {current_port}\nBaud Rate: {current_baud}\n\n"
        
        # 2. Clear any old junk from the AI's ears
        from queue import Empty
        import time
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except Empty:
                break
                
        # 3. Ask the printer for its M115 hardware ID
        self.p.send_now("M115")
        
        response = ""
        start_time = time.time()
        timeout = 2.5  # Wait 2.5 seconds for the printer to dump its hardware text
        
        while time.time() - start_time < timeout:
            try:
                # Listen for the terminal output
                line = str(self.log_queue.get(timeout=0.2)).strip()
                if line:
                    response += line + "\n"
            except Empty:
                continue

        # 4. Combine the Pronterface connection data with the Printer's M115 data
        if response:
            return f"{connection_header}=== HARDWARE & FIRMWARE REPORT ===\n{response}"
        return f"{connection_header}Command sent, but no recognizable M115 hardware info was returned."

    def run_diagnostics(self) -> str:
        """Runs hardware diagnostics including endstop status (M119) and current temperatures (M105)."""
        if not (self.p and self.p.online):
            return "Diagnostic Failed: Printer is not connected."

        # Clear out any old terminal messages so we only get fresh data
        from queue import Empty
        import time
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except Empty:
                break

        report = "=== PRINTER HEALTH DIAGNOSTICS ===\n"

        # 1. Temperature Check (M105) - Checks for broken thermistor wires
        self.p.send_now("M105")
        time.sleep(0.5)
        temp_str = ""
        while not self.log_queue.empty():
            try:
                temp_str += str(self.log_queue.get_nowait()) + "\n"
            except Empty:
                break
        report += f"Temperatures:\n{temp_str.strip() if temp_str else 'NO RESPONSE'}\n\n"

        # 2. Endstop Check (M119) - Checks for jammed or broken limit switches
        self.p.send_now("M119")
        time.sleep(0.5)
        endstop_str = ""
        while not self.log_queue.empty():
            try:
                endstop_str += str(self.log_queue.get_nowait()) + "\n"
            except Empty:
                break
        report += f"Endstops (M119):\n{endstop_str.strip() if endstop_str else 'NO RESPONSE'}\n"

        return report
    
    def disconnect_printer(self) -> str:
        """
        Disconnects from the 3D printer.

        Returns:
            A status message.
        """
        if self.p and self.p.online:
            try:
                self.p.disconnect()
                self.p = None
                return "Disconnected from printer."
            except Exception as e:
                return f"An error occurred during disconnection: {e}"
        return "Not connected to any printer."

    def get_printer_status(self) -> str:
        """
        Checks the connection status of the printer.

        Returns:
            A string indicating the printer's status (online, offline, printing, paused).
        """
        if not self.p:
            return "Printer is offline (not connected)."
        status = []
        if self.p.online:
            status.append("Online")
            if self.p.printing:
                status.append("Printing")
            elif self.p.paused:
                status.append("Paused")
            else:
                status.append("Idle")
        else:
            status.append("Offline")
        return "Status: " + ", ".join(status)

    def send_raw_gcode(self, command: str) -> str:
        """
        Sends a raw G-code command directly to the printer.

        Args:
            command: The G-code command string (e.g., "M105").

        Returns:
            A status message indicating success or failure.
        """
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        try:
            self.p.send_now(command)
            # For immediate commands like M105, we might want to wait for a response
            # printcore's send_now is non-blocking. A more advanced wrapper
            # would need to parse responses from the log_queue.
            time.sleep(0.1) # Give a small moment for printer to process
            response = ""
            while not self.log_queue.empty():
                response += str(self.log_queue.get_nowait()) + "\n"
            return f"Command '{command}' sent. Printer response (if any):\n{response.strip()}"
        except Exception as e:
            return f"Error sending command '{command}': {e}"

    def load_gcode_file(self, filepath: str) -> str:
        """
        Loads a G-code file for printing. This does not start the print.

        Args:
            filepath: The path to the G-code file.

        Returns:
            A status message.
        """
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        try:
            with open(filepath, 'r') as f:
                gcode_lines = [line.strip() for line in f if line.strip()]
            self.p.mainqueue = gcoder.GCode(gcode_lines)
            return f"G-code file '{filepath}' loaded successfully."
        except FileNotFoundError:
            return f"Error: File '{filepath}' not found."
        except Exception as e:
            return f"Error loading G-code file: {e}"

    def start_print(self) -> str:
        """
        Starts the printing process for the currently loaded G-code.

        Returns:
            A status message.
        """
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        if not self.p.mainqueue:
            return "No G-code file loaded to print."
        
        # printcore.startprint expects a gcoder.GCode object, not just lines
        # if self.p.mainqueue is already a GCode object from load_gcode_file,
        # then this is fine. If it's a list, it needs to be converted.
        # Assuming load_gcode_file already sets self.p.mainqueue as a GCode object.
        
        if self.p.startprint(self.p.mainqueue):
            return "Print started."
        else:
            return "Failed to start print (printer might be busy or offline)."

    def pause_print(self) -> str:
        """
        Pauses an active print job.

        Returns:
            A status message.
        """
        if not (self.p and self.p.online and self.p.printing):
            return "No active print to pause."
        self.p.pause()
        return "Print paused."

    def resume_print(self) -> str:
        """
        Resumes a paused print job.

        Returns:
            A status message.
        """
        if not (self.p and self.p.online and self.p.paused):
            return "No paused print to resume."
        self.p.resume()
        return "Print resumed."

    def cancel_print(self) -> str:
        """
        Aborts the current print job.

        Returns:
            A status message.
        """
        if not (self.p and self.p.online and (self.p.printing or self.p.paused)):
            return "No active or paused print to cancel."
        self.p.cancelprint()
        return "Print cancelled."

    def get_print_progress(self) -> str:
        """
        Retrieves the status of the current print.

        Returns:
            A string with print progress information.
        """
        if not (self.p and self.p.online and self.p.printing):
            return "No active print to report progress."
        
        # printcore doesn't directly expose percentage progress.
        # We can infer it if mainqueue and queueindex are available.
        if self.p.mainqueue and self.p.mainqueue.lines:
            total_lines = len(self.p.mainqueue.lines)
            current_line = self.p.queueindex
            if total_lines > 0:
                percentage = (current_line / total_lines) * 100
                return f"Print in progress: {percentage:.2f}% complete (line {current_line}/{total_lines})."
        return "Print in progress, but progress information is limited."

    def set_temperatures(self, tool_temp: int = None, bed_temp: int = None) -> str:
        """
        Sets target temperatures for the hotend and/or heated bed.

        Args:
            tool_temp: Target temperature for the hotend (e.g., 200).
            bed_temp: Target temperature for the heated bed (e.g., 60).

        Returns:
            A status message.
        """
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        commands = []
        if tool_temp is not None:
            commands.append(f"M104 S{tool_temp}") # Set hotend temperature
        if bed_temp is not None:
            commands.append(f"M140 S{bed_temp}") # Set bed temperature
        
        if not commands:
            return "No temperatures specified to set."
        
        results = []
        for cmd in commands:
            self.p.send_now(cmd)
            results.append(f"Sent: {cmd}")
        return "\n".join(results)

    def get_temperatures(self) -> str:
        """
        Reads the current temperatures of the hotend and heated bed.

        Returns:
            A string with current temperature readings.
        """
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        
        self.p.send_now("M105") # Request temperatures
        time.sleep(0.5) # Give printer time to respond
        
        response = ""
        while not self.log_queue.empty():
            response += str(self.log_queue.get_nowait()) + "\n"
        
        if "T:" in response or "B:" in response:
            return f"Current temperatures:\n{response.strip()}"
        return "Could not retrieve temperature information. Ensure printer is responsive."

    # Placeholder for more complex tools like move_printhead, home_axes, extrude_filament
    # These would involve more detailed G-code commands and state management.
    def move_printhead(self, x: float = None, y: float = None, z: float = None, speed: int = None) -> str:
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
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        
        coords = []
        if x is not None: coords.append(f"X{x}")
        if y is not None: coords.append(f"Y{y}")
        if z is not None: coords.append(f"Z{z}")
        
        if not coords:
            return "No coordinates specified for movement."
            
        speed_cmd = f"F{speed}" if speed is not None else ""
        gcode_cmd = f"G0 { ' '.join(coords) } {speed_cmd}".strip()
        
        self.p.send_now("G90") # Ensure absolute positioning
        self.p.send_now(gcode_cmd)
        return f"Sent move command: {gcode_cmd}"

    def extrude_filament(self, amount: float, speed: int = None, retract: bool = False) -> str:
        """
        Extrudes or retracts filament.

        Args:
            amount: The amount of filament to extrude/retract in mm.
            speed: The feed rate for extrusion/retraction in mm/min.
            retract: If True, retracts filament. Otherwise, extrudes.

        Returns:
            A status message.
        """
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        
        gcode_cmd = f"G1 E{ -amount if retract else amount}"
        if speed is not None:
            gcode_cmd += f" F{speed}"
            
        self.p.send_now("M83") # Ensure relative extrusion positioning
        self.p.send_now(gcode_cmd)
        self.p.send_now("M82") # Revert to absolute extrusion positioning (common default)
        
        action = "Retracted" if retract else "Extruded"
        return f"{action} {amount}mm of filament."
        
    # SD Card operations (placeholders, as printcore itself doesn't directly handle these easily)
    
    def list_sd_files(self) -> str:
        """Lists files on the printer's SD card by listening for the 'End file list' marker."""
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        
        # Clear any old junk from the AI's ears
        while not self.log_queue.empty():
            self.log_queue.get_nowait()
            
        self.p.send_now("M20")
        
        response = ""
        start_time = time.time()
        timeout = 5  # Give the printer up to 5 seconds to send the whole list
        
        while time.time() - start_time < timeout:
            try:
                # Wait for new lines from the printer
                line = str(self.log_queue.get(timeout=0.5))
                response += line + "\n"
                
                # M20 responses always conclude with this exact string
                if "End file list" in line:
                    break
            except Empty:
                continue

        if "Begin file list" in response:
            # Clean up the output so it looks nice for the AI
            lines = response.split('\n')
            files = [l for l in lines if ".GCO" in l or ".gcode" in l]
            return f"SD Card Files:\n" + "\n".join(files)
            
        return "Could not retrieve SD card file list. Printer might not support M20 or SD card not present."

    def upload_to_sd(self, local_filepath: str, remote_filename: str = None) -> str:
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
        return "SD card upload is not directly supported via printcore's simple API. This feature would require custom implementation or external tools."

    def print_from_sd(self, filename: str) -> str:
        """
        Starts a print from a G-code file on the SD card. (Requires printer support for M23/M24)

        Args:
            filename: The name of the G-code file on the SD card.

        Returns:
            A status message.
        """
        if not (self.p and self.p.online):
            return "Printer is not connected or online."
        
        self.p.send_now(f"M23 {filename}") # Select file
        time.sleep(0.1)
        self.p.send_now("M24") # Start SD print
        return f"Attempted to start print from SD card: {filename}. Check printer display for status."