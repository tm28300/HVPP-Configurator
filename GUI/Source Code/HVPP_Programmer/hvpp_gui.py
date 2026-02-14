#!/usr/bin/env python3
"""
AVR High Voltage Parallel Programmer GUI
Cross-platform GUI using tkinter (compatible with Windows, Linux x86_64, Linux ARM64)
"""

import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional
from hvpp_programmer import AtmelHighVoltageParallelProgrammer, HVPPCommand

# Debug messages control variable
DEBUG_PRINT = False


class HVPPConfiguratorGUI:
    """Main GUI application for HVPP Configurator"""

    # Available chip types
    CHIP_TYPES = [
        "ATMEGA8(A)(L)",
        "ATMEGA48",
        "ATMEGA168(P)(PA)",
        "ATMEGA328(P)",
        "ATTINY2313(V)",
        "ATMEGA1284(P)"
    ]

    def __init__(self, root: tk.Tk):
        """
        Initialize the GUI

        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title("AVR Micro Processor HVPP Configurator GUI v1.0 (Python Edition)")
        self.root.resizable(False, False)

        # Set application icon (extracted from original C# resources)
        try:
            base_path = Path(__file__).parent
            if sys.platform.startswith("win"):
                icon_path = base_path / "app_icon.ico"
                if icon_path.exists():
                    self.root.iconbitmap(str(icon_path))
                elif DEBUG_PRINT:
                    print("Windows icon file not found.")
            else:
                icon_path = base_path / "app_icon.png"
                if icon_path.exists():
                    self._icon_image = tk.PhotoImage(file=str(icon_path))
                    self.root.iconphoto(True, self._icon_image)
                elif DEBUG_PRINT:
                    print("Linux icon file not found.")
        except Exception as ex:
            if DEBUG_PRINT:
                print(f"Failed to set icon: {ex}")

        self.programmer: Optional[AtmelHighVoltageParallelProgrammer] = None
        self._operation_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._busy = False

        self._create_widgets()
        self._load_ports()

        self._init_busy_widgets()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_widgets(self):
        """Create all GUI widgets"""

        # ===== Menu Bar =====
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

# Tools Menu
        outils_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=outils_menu)

        # Programmer Log option (disabled by default)
        outils_menu.add_command(label="Programmer Log", command=self._on_log_programmer, state="disabled")
        self.log_menu_item = outils_menu
        self.log_menu_index = 0  # Option index in menu

        outils_menu.add_separator()
        outils_menu.add_command(label="Quit", command=self._on_exit)

# Help Menu
        aide_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=aide_menu)
        aide_menu.add_command(label="About", command=self._on_about)

        # ===== ATMEL Chip Section =====
        chip_frame = ttk.LabelFrame(self.root, text="ATMEL Chip", padding=10)
        chip_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        # Target Chip
        ttk.Label(chip_frame, text="Target Chip:").grid(row=0, column=0, sticky="w", padx=5)
        self.chip_combo = ttk.Combobox(chip_frame, values=self.CHIP_TYPES, state="readonly", width=18)
        self.chip_combo.grid(row=0, column=1, padx=5)

        # Port
        ttk.Label(chip_frame, text="Port:").grid(row=0, column=2, sticky="w", padx=5)
        self.port_combo = ttk.Combobox(chip_frame, state="readonly", width=10)
        self.port_combo.grid(row=0, column=3, padx=5)

        # Connect button
        self.connect_btn = ttk.Button(chip_frame, text="Connect", command=self._on_connect)
        self.connect_btn.grid(row=0, column=4, padx=5)

        # Chip Signature
        ttk.Label(chip_frame, text="Chip Signature:").grid(row=0, column=5, sticky="w", padx=5)
        self.signature_entry = ttk.Entry(chip_frame, width=12, justify="center")
        self.signature_entry.grid(row=0, column=6, padx=5)

        # Read Signature button
        self.read_sig_btn = ttk.Button(chip_frame, text="Read Signature", command=self._on_read_signature)
        self.read_sig_btn.grid(row=0, column=7, padx=5)

        # ===== Chip Functions Section =====
        func_frame = ttk.LabelFrame(self.root, text="Chip Functions", padding=10)
        func_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        # Calibration Byte
        ttk.Label(func_frame, text="Calibration Byte:").grid(row=0, column=0, sticky="w", padx=5)
        self.calibration_entry = ttk.Entry(func_frame, width=10, justify="center")
        self.calibration_entry.grid(row=0, column=1, padx=5)

        # Read Calibration button
        self.read_cal_btn = ttk.Button(func_frame, text="Read Calibration Byte", command=self._on_read_calibration)
        self.read_cal_btn.grid(row=0, column=2, padx=5)

        # Erase Chip button
        self.erase_btn = ttk.Button(func_frame, text="Erase Chip", command=self._on_erase_chip)
        self.erase_btn.grid(row=0, column=3, padx=5)

        # Write Lock Byte button
        self.lock_btn = ttk.Button(func_frame, text="Write Lock Byte", command=self._on_write_lock)
        self.lock_btn.grid(row=0, column=4, padx=5)

        # ===== Fuse Settings Section =====
        fuse_frame = ttk.LabelFrame(self.root, text="Fuse Settings", padding=10)
        fuse_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        # Low Fuse
        ttk.Label(fuse_frame, text="Low Fuse:").grid(row=0, column=0, sticky="w", padx=5)
        self.lfuse_entry = ttk.Entry(fuse_frame, width=10, justify="center")
        self.lfuse_entry.grid(row=0, column=1, padx=5)

        # High Fuse
        ttk.Label(fuse_frame, text="High Fuse:").grid(row=0, column=2, sticky="w", padx=5)
        self.hfuse_entry = ttk.Entry(fuse_frame, width=10, justify="center")
        self.hfuse_entry.grid(row=0, column=3, padx=5)

        # Extended Fuse
        ttk.Label(fuse_frame, text="Extended Fuse:").grid(row=0, column=4, sticky="w", padx=5)
        self.efuse_entry = ttk.Entry(fuse_frame, width=10, justify="center")
        self.efuse_entry.grid(row=0, column=5, padx=5)

        # Lock Byte
        ttk.Label(fuse_frame, text="Lock Byte:").grid(row=0, column=6, sticky="w", padx=5)
        self.lock_entry = ttk.Entry(fuse_frame, width=10, justify="center")
        self.lock_entry.grid(row=0, column=7, padx=5)

        # Read Fuses button
        self.read_fuses_btn = ttk.Button(fuse_frame, text="Read Fuses", command=self._on_read_fuses)
        self.read_fuses_btn.grid(row=0, column=8, padx=5)

        # Write buttons
        self.write_lfuse_btn = ttk.Button(fuse_frame, text="Write Low Fuse", command=self._on_write_lfuse)
        self.write_lfuse_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=5)

        self.write_hfuse_btn = ttk.Button(fuse_frame, text="Write High Fuse", command=self._on_write_hfuse)
        self.write_hfuse_btn.grid(row=1, column=2, columnspan=2, padx=5, pady=5)

        self.write_efuse_btn = ttk.Button(fuse_frame, text="Write Extended Fuse", command=self._on_write_efuse)
        self.write_efuse_btn.grid(row=1, column=4, columnspan=2, padx=5, pady=5)

        # ===== Memory Operations Section =====
        memory_frame = ttk.LabelFrame(self.root, text="Memory Operations", padding=10)
        memory_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        # Flash memory buttons
        self.read_flash_btn = ttk.Button(memory_frame, text="Read Flash Memory", command=self._on_read_flash)
        self.read_flash_btn.grid(row=0, column=0, padx=5, pady=5)

        self.write_flash_btn = ttk.Button(memory_frame, text="Write Flash Memory", command=self._on_write_flash)
        self.write_flash_btn.grid(row=0, column=1, padx=5, pady=5)

        # EEPROM memory buttons
        self.read_eeprom_btn = ttk.Button(memory_frame, text="Read EEPROM Memory", command=self._on_read_eeprom)
        self.read_eeprom_btn.grid(row=0, column=2, padx=5, pady=5)

        self.write_eeprom_btn = ttk.Button(memory_frame, text="Write EEPROM Memory", command=self._on_write_eeprom)
        self.write_eeprom_btn.grid(row=0, column=3, padx=5, pady=5)

        self.stop_btn = ttk.Button(memory_frame, text="Stop", command=self._on_stop, state="disabled")
        self.stop_btn.grid(row=0, column=4, padx=5, pady=5)

        # Progress bar for memory operations
        self.progress_bar = ttk.Progressbar(memory_frame, orient="horizontal", mode="determinate", length=300)
        self.progress_bar.grid(row=1, column=0, columnspan=5, sticky="ew", padx=5, pady=(5, 0))
        self.operation_label = ttk.Label(memory_frame, text="")
        self.operation_label.grid(row=2, column=0, columnspan=5, sticky="w", padx=5, pady=(0, 2))
        self.progress_label = ttk.Label(memory_frame, text="")
        self.progress_label.grid(row=3, column=0, columnspan=5, sticky="w", padx=5, pady=(0, 5))

        # ===== Bottom Buttons =====
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=4, column=0, padx=10, pady=10, sticky="e")

        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", command=self._on_disconnect)
        self.disconnect_btn.grid(row=0, column=0, padx=5)

        self.exit_btn = ttk.Button(button_frame, text="Exit", command=self._on_exit)
        self.exit_btn.grid(row=0, column=1, padx=5)

    def _load_ports(self):
        """Load available serial ports"""
        ports = AtmelHighVoltageParallelProgrammer.get_available_ports()
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def _init_busy_widgets(self):
        """Track widgets that should be disabled during background operations."""
        self._busy_widgets = [
            self.chip_combo,
            self.port_combo,
            self.connect_btn,
            self.read_sig_btn,
            self.read_cal_btn,
            self.erase_btn,
            self.lock_btn,
            self.read_fuses_btn,
            self.write_lfuse_btn,
            self.write_hfuse_btn,
            self.write_efuse_btn,
            self.disconnect_btn,
            self.read_flash_btn,
            self.write_flash_btn,
            self.read_eeprom_btn,
            self.write_eeprom_btn,
        ]
        self._busy_widget_states = {widget: widget.cget("state") for widget in self._busy_widgets}

    def _set_controls_busy(self, busy: bool):
        """Enable/disable controls during long-running operations."""
        for widget in self._busy_widgets:
            if busy:
                widget.config(state="disabled")
            else:
                original_state = self._busy_widget_states.get(widget, "normal")
                widget.config(state=original_state)

        if busy:
            self.log_menu_item.entryconfig(self.log_menu_index, state="disabled")
            self.stop_btn.config(state="normal")
        else:
            if self.programmer:
                self.log_menu_item.entryconfig(self.log_menu_index, state="normal")
            self.stop_btn.config(state="disabled")

    def _clear_progress(self):
        """Clear progress bar and labels."""
        self.progress_bar["value"] = 0
        self.operation_label.config(text="")
        self.progress_label.config(text="")

    def _on_connect(self):
        """Handle Connect button click"""
        chip = self.chip_combo.get()
        port = self.port_combo.get()

        if not chip or not port:
            messagebox.showerror("Error",
                "Please select the chip and serial port before connecting to the programmer.")
            return

        try:
            if self.programmer:
                self.programmer.close()

            self.programmer = AtmelHighVoltageParallelProgrammer(port, chip)
            # Enable Programmer Log option upon object creation
            self.log_menu_item.entryconfig(self.log_menu_index, state="normal")

            result = self.programmer.programmer_communicate(HVPPCommand.OPEN, "")

            if result == "0":
                messagebox.showinfo("Information",
                    "HVPP mode has been enabled successfully.")
            else:
                messagebox.showerror("Error",
                    "Error communicating with the programmer.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")

    def _on_read_signature(self):
        """Handle Read Signature button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.READ_SIGNATURE, "")
        self.signature_entry.delete(0, tk.END)
        self.signature_entry.insert(0, result)

    def _on_disconnect(self):
        """Handle Disconnect button click"""
        if self.programmer:
            result = self.programmer.programmer_communicate(HVPPCommand.END, "")

            if result == "0":
                messagebox.showinfo("Information",
                    "HVPP mode has ended successfully.")
                # Disable Programmer Log option
                self.log_menu_item.entryconfig(self.log_menu_index, state="disabled")

                # Clear all displayed data
                self.signature_entry.delete(0, tk.END)
                self.calibration_entry.delete(0, tk.END)
                self.lfuse_entry.delete(0, tk.END)
                self.hfuse_entry.delete(0, tk.END)
                self.efuse_entry.delete(0, tk.END)
                self.lock_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error",
                    "Error communicating with the programmer.")

    def _on_read_fuses(self):
        """Handle Read Fuses button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.READ_FUSES, "")
        if DEBUG_PRINT:
            print(f"DEBUG _on_read_fuses: résultat brut = '{result}' (longueur: {len(result)})")

        fuses = result.split(' ')
        if DEBUG_PRINT:
            print(f"DEBUG _on_read_fuses: fuses après split = {fuses} (nombre: {len(fuses)})")
        if len(fuses) >= 4:
            self.lfuse_entry.delete(0, tk.END)
            self.lfuse_entry.insert(0, fuses[0])

            self.hfuse_entry.delete(0, tk.END)
            self.hfuse_entry.insert(0, fuses[1])

            self.efuse_entry.delete(0, tk.END)
            self.efuse_entry.insert(0, fuses[2])

            self.lock_entry.delete(0, tk.END)
            self.lock_entry.insert(0, fuses[3])
            if DEBUG_PRINT:
                print("DEBUG _on_read_fuses: data displayed in fields")
        else:
            messagebox.showerror("Error", f"Invalid response format. Received: '{result}' ({len(fuses)} elements instead of 4)")

    def _on_read_calibration(self):
        """Handle Read Calibration Byte button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.READ_CALIBRATION_BYTE, "")
        self.calibration_entry.delete(0, tk.END)
        self.calibration_entry.insert(0, result)

    def _on_write_lfuse(self):
        """Handle Write Low Fuse button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        lfuse = self.lfuse_entry.get()
        if not lfuse:
            messagebox.showerror("Error", "Low fuse cannot be empty.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.WRITE_LFUSE, lfuse)

        if result == "0":
            messagebox.showinfo("Information", "Low fuse has been saved successfully.")
        else:
            messagebox.showerror("Error", "Error communicating with the programmer.")

    def _on_write_hfuse(self):
        """Handle Write High Fuse button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        hfuse = self.hfuse_entry.get()
        if not hfuse:
            messagebox.showerror("Error", "High fuse cannot be empty.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.WRITE_HFUSE, hfuse)

        if result == "0":
            messagebox.showinfo("Information", "High fuse has been saved successfully.")
        else:
            messagebox.showerror("Error", "Error communicating with the programmer.")

    def _on_write_efuse(self):
        """Handle Write Extended Fuse button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        efuse = self.efuse_entry.get()
        if not efuse:
            messagebox.showerror("Error", "Extended fuse cannot be empty.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.WRITE_EXT_FUSE, efuse)

        if result == "0":
            messagebox.showinfo("Information", "Extended fuse has been saved successfully.")
        else:
            messagebox.showerror("Error", "Error communicating with the programmer.")

    def _on_erase_chip(self):
        """Handle Erase Chip button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.CHIP_ERASE, "")

        if result == "0":
            messagebox.showinfo("Information", "Chip has been erased successfully.")
        else:
            messagebox.showerror("Error", "Error communicating with the programmer.")

    def _on_write_lock(self):
        """Handle Write Lock Byte button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        result = self.programmer.programmer_communicate(HVPPCommand.WRITE_LOCK_BYTE, "")

        if result == "0":
            messagebox.showinfo("Information", "Lock byte has been saved successfully.")
        else:
            messagebox.showerror("Error", "Error communicating with the programmer.")

    def _on_log_programmer(self):
        """Handle Programmer Log menu option"""
        if not self.programmer:
            return

        try:
            # Send LOG command (97) with timeout
            result = self.programmer.programmer_communicate(HVPPCommand.LOG, "")

            # Remove only trailing newline
            result = result.rstrip('\r\n')

            # Create custom window to display log
            log_window = tk.Toplevel(self.root)
            log_window.title("Programmer Log")
            log_window.geometry("600x400")

            # Text widget to display log with line breaks
            text_widget = tk.Text(log_window, wrap=tk.WORD, padx=10, pady=10)
            text_widget.pack(expand=True, fill=tk.BOTH)

            # Insert text
            text_widget.insert("1.0", result if result else "No log received")
            text_widget.config(state=tk.DISABLED)  # Read only

            # OK button to close
            ok_btn = ttk.Button(log_window, text="OK", command=log_window.destroy)
            ok_btn.pack(pady=5)

        except Exception as e:
            messagebox.showerror("Error", f"Error reading log: {str(e)}")

    def _set_busy(self, busy: bool):
        """Set busy cursor during long operations"""
        cursor = "watch" if busy else ""
        try:
            self.root.config(cursor=cursor)
            self.root.update_idletasks()
        except tk.TclError:
            cursor = "wait" if busy else ""
            try:
                self.root.config(cursor=cursor)
                self.root.update_idletasks()
            except tk.TclError:
                pass

    def _update_progress(self, label: str, current: int, total: int):
        """Update progress bar and label"""
        if total <= 0:
            return
        self.progress_bar["maximum"] = total
        self.progress_bar["value"] = current
        self.progress_label.config(text=f"{current}/{total}")
        self.root.update_idletasks()

    def _start_memory_operation(
        self,
        label: str,
        command: str,
        filename: str,
        success_message: str,
        hvpp_command: HVPPCommand = HVPPCommand.READ_MEMORY,
    ):
        """Start memory operation in a background thread."""
        if self._operation_thread and self._operation_thread.is_alive():
            return

        self._busy = True
        self._stop_event.clear()
        self._clear_progress()
        self.operation_label.config(text=label)
        self._set_busy(True)
        self._set_controls_busy(True)

        def progress_cb(current: int, total: int):
            self.root.after(0, self._update_progress, label, current, total)

        def finish(result: Optional[str], error: Optional[Exception]):
            self._set_busy(False)
            self._set_controls_busy(False)
            self._busy = False

            if error:
                if str(error) != "Operation stopped":
                    messagebox.showerror("Error", f"{label} failed: {str(error)}")
                self._clear_progress()
                return

            if result == "0":
                messagebox.showinfo("Success", success_message)
            else:
                messagebox.showerror("Error", f"{label} failed.")
            self._clear_progress()

        def worker():
            try:
                result = self.programmer.programmer_communicate(
                    hvpp_command,
                    command,
                    progress_callback=progress_cb,
                    stop_event=self._stop_event,
                )
                self.root.after(0, finish, result, None)
            except Exception as exc:
                self.root.after(0, finish, None, exc)

        self._operation_thread = threading.Thread(target=worker, daemon=True)
        self._operation_thread.start()

    def _on_stop(self):
        """Handle Stop button click"""
        if self._busy:
            self.operation_label.config(text="Arrêt en cours...")
            self.stop_btn.config(state="disabled")
            self._stop_event.set()

    def _on_read_flash(self):
        """Handle Read Flash Memory button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        # Ask user for output file
        filename = filedialog.asksaveasfilename(
            title="Save Flash Memory",
            defaultextension=".hex",
            filetypes=[("Intel HEX files", "*.hex"), ("All files", "*.*")]
        )

        if not filename:
            return  # User cancelled

        self._start_memory_operation(
            label="Lecture Flash",
            command=f"flash:{filename}",
            filename=filename,
            success_message=f"Flash memory successfully read and saved to:\n{filename}",
            hvpp_command=HVPPCommand.READ_MEMORY,
        )

    def _on_read_eeprom(self):
        """Handle Read EEPROM Memory button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        # Ask user for output file
        filename = filedialog.asksaveasfilename(
            title="Save EEPROM Memory",
            defaultextension=".hex",
            filetypes=[("Intel HEX files", "*.hex"), ("All files", "*.*")]
        )

        if not filename:
            return  # User cancelled

        self._start_memory_operation(
            label="Lecture EEPROM",
            command=f"eeprom:{filename}",
            filename=filename,
            success_message=f"EEPROM memory successfully read and saved to:\n{filename}",
            hvpp_command=HVPPCommand.READ_MEMORY,
        )

    def _on_write_flash(self):
        """Handle Write Flash Memory button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        filename = filedialog.askopenfilename(
            title="Open Flash Memory HEX",
            filetypes=[("Intel HEX files", "*.hex"), ("All files", "*.*")]
        )

        if not filename:
            return

        self._start_memory_operation(
            label="Écriture Flash",
            command=f"flash:{filename}",
            filename=filename,
            success_message=f"Flash memory successfully written from:\n{filename}",
            hvpp_command=HVPPCommand.WRITE_MEMORY,
        )

    def _on_write_eeprom(self):
        """Handle Write EEPROM Memory button click"""
        if not self.programmer:
            messagebox.showwarning("Warning", "Please connect to the programmer first.")
            return

        filename = filedialog.askopenfilename(
            title="Open EEPROM Memory HEX",
            filetypes=[("Intel HEX files", "*.hex"), ("All files", "*.*")]
        )

        if not filename:
            return

        self._start_memory_operation(
            label="Écriture EEPROM",
            command=f"eeprom:{filename}",
            filename=filename,
            success_message=f"EEPROM memory successfully written from:\n{filename}",
            hvpp_command=HVPPCommand.WRITE_MEMORY,
        )

    def _on_exit(self):
        """Handle Exit button click"""
        if self.programmer:
            self.programmer.programmer_communicate(HVPPCommand.END, "")
            # Disable Programmer Log option
            self.log_menu_item.entryconfig(self.log_menu_index, state="disabled")
        self.root.quit()

    def _on_about(self):
        """Handle À propos menu option"""
        # Créer une fenêtre À propos
        about_window = tk.Toplevel(self.root)
        about_window.title("À propos")
        about_window.geometry("400x275")
        about_window.resizable(False, False)

        # Titre
        title_label = tk.Label(about_window, text="AVR HVPP Configurator GUI",
                              font=("Arial", 16, "bold"), pady=10)
        title_label.pack()

        # Version du logiciel
        version_label = tk.Label(about_window, text="Version 1.0 (Python Edition)",
                                font=("Arial", 10))
        version_label.pack()

        # Séparateur
        separator = ttk.Separator(about_window, orient="horizontal")
        separator.pack(fill="x", padx=20, pady=10)

        # Infos du firmware si connecté
        if self.programmer and hasattr(self.programmer, 'firmware_info') and self.programmer.firmware_info:
            firmware_frame = tk.Frame(about_window)
            firmware_frame.pack(pady=10)

            fw_title = tk.Label(firmware_frame, text="Programmer firmware:",
                               font=("Arial", 10, "bold"))
            fw_title.pack()

            fw_info = tk.Label(firmware_frame, text=self.programmer.firmware_info,
                              font=("Arial", 9))
            fw_info.pack(pady=5)
        else:
            status_label = tk.Label(about_window, text="Programmer not connected",
                                   font=("Arial", 9, "italic"), fg="gray")
            status_label.pack(pady=10)

        # Credits
        credits_frame = tk.Frame(about_window)
        credits_frame.pack(pady=10)

        credit1 = tk.Label(credits_frame, text="Version C# originale: Shichang Zhuo",
                          font=("Arial", 8))
        credit1.pack()

        credit2 = tk.Label(credits_frame, text="Porté en Python par Thierry (2025)",
                          font=("Arial", 8))
        credit2.pack()

        # Bouton OK
        ok_btn = ttk.Button(about_window, text="OK", command=about_window.destroy)
        ok_btn.pack(pady=10)

    def _on_closing(self):
        """Handle window close event"""
        if self.programmer:
            self.programmer.programmer_communicate(HVPPCommand.END, "")
        self.root.destroy()


def main():
    """Main entry point"""
    root = tk.Tk(className="HVPP Configurator")
    app = HVPPConfiguratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
