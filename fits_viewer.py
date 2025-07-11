#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FITS Viewer
-----------
Author: Generated by Chat-GPT 4o, Grok 3 (xAI), under instructions given by T. Zoeller
Date: July 06, 2025
Version: 1.5
Description:
    A lightweight Python-based GUI tool for viewing and navigating tabular data
    and images in FITS (Flexible Image Transport System) files. The tool dynamically
    loads column names from the first available BinTableHDU or TableHDU for tabular
    data display, allowing users to select columns, adjust display settings (row counts,
    column widths, font sizes), and navigate through pages. If no tabular data is found,
    the main window remains open, displaying a message in the text area and keeping
    the column selection empty, with an option to open the Image Viewer for image data.
    The Image Viewer displays image HDUs with zoom, rotation, and real-time RA/DEC
    coordinate display using WCS. The tool supports large files via memory mapping
    (memmap=True) with fallback to memmap=False for compatibility.

Requirements:
    - Python 3.x
    - astropy (for FITS file handling and WCS)
    - numpy (for data processing)
    - tkinter (typically included with Python, for GUI)
    - PIL (Pillow, for image processing)
    - matplotlib (for image rendering)

Notes:
    - Suppresses `FITSFixedWarning` via direct import: `from astropy.wcs import FITSFixedWarning`

Usage:
    Run with: python fits_browser.py <fits_file_path>
    or use the provided fview.bat script: fview <fits_file_path>
    - Use mouse wheel for page up/down in the Table Viewer or image navigation in the Image Viewer.
    - In Image Viewer: Use "Zoom +"/"Zoom -" for scaling, "Rotate Left"/"Rotate Right" for 90-degree rotations,
      "Previous"/"Next" for image navigation, and move the mouse over the image to see RA/DEC coordinates.

Features:
    - Table Viewer: Dynamic column selection, customizable row counts, column widths, and font sizes.
    - Image Viewer: Displays image HDUs with zoom (20% steps), rotation (±90°), navigation,
      and real-time RA/DEC coordinate display using WCS.
    - Memory-efficient handling of large FITS files via memmap=True with fallback to memmap=False.
    - Centered GUI windows with consistent size (1800x950 pixels) for both Table and Image Viewers.
    - Displays a message in the main window if no tabular data is found, with an option to open the Image Viewer.

Limitations:
    - Table Viewer requires a BinTableHDU or TableHDU in the FITS file.
    - Image Viewer supports only ImageHDU and PrimaryHDU with non-empty data.
    - RA/DEC coordinate display requires valid WCS in the FITS header.
    - Large files (>6 GB) may strain memory despite memmap.
    - No search functionality in the Table Viewer.
    - Zoom and rotation in the Image Viewer are applied only to the display, not to the FITS data itself.
"""

import sys
import warnings
import os
import io

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

import numpy as np
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import matplotlib.cm as cm

from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning

# Suppress specific FITS header warnings from astropy
warnings.filterwarnings('ignore', category=FITSFixedWarning)

class ImageViewer:
    def __init__(self, file_path):
        """Initialize the Image Viewer for displaying FITS image HDUs."""
        global USE_MEMMAP
        self.file_path = file_path
        self.wcs = None  # Initialize wcs as None
        self.tooltip = None  # Initialize tooltip

        # Open FITS file with memmap, fallback to memmap=False if needed
        try:
            self.hdul = fits.open(file_path, memmap=USE_MEMMAP)
        except ValueError as e:
            if 'BZERO/BSCALE/BLANK' in str(e):
                self.hdul = fits.open(file_path, memmap=False)
                USE_MEMMAP = False
                messagebox.showinfo("Memmap Disabled", "BZERO/BSCALE/BLANK headers detected. Opened without memmap.")
            else:
                raise e

        # Check HDUs for valid image data
        self.image_hdus = []
        for hdu in self.hdul:
            if isinstance(hdu, (fits.ImageHDU, fits.PrimaryHDU)):
                try:
                    if hdu.data is not None:
                        self.image_hdus.append(hdu)
                except ValueError as e:
                    if 'BZERO/BSCALE/BLANK' in str(e):
                        self.hdul.close()
                        self.hdul = fits.open(self.file_path, memmap=False)
                        USE_MEMMAP = False
                        for hdu_retry in self.hdul:
                            if isinstance(hdu_retry, (fits.ImageHDU, fits.PrimaryHDU)) and hdu_retry.data is not None:
                                self.image_hdus.append(hdu_retry)
                        break
                    else:
                        raise e

        # Check all HDUs for WCS information
        for hdu in self.hdul:
            try:
                self.wcs = WCS(hdu.header, relax=True)
                print(f"WCS found in HDU #{self.hdul.index(hdu)}")
                break
            except Exception as e:
                print(f"No WCS in HDU #{self.hdul.index(hdu)}: {str(e)}")
                continue

        if not self.image_hdus:
            messagebox.showinfo("No Images", "No image HDUs found in this file.")
            self.hdul.close()
            return

        self.index = 0
        self.zoom_factor = 1.0
        self.rotation_angle = 0

        self.win = tk.Toplevel()
        self.win.title("FITS Image Viewer")
        self.win.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.center_window()

        self.win.bind("<MouseWheel>", self.on_mousewheel)
        self.win.bind("<Button-4>", self.on_mousewheel_linux)
        self.win.bind("<Button-5>", self.on_mousewheel_linux)

        main_frame = ttk.Frame(self.win)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=0)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)

        self.canvas = tk.Label(main_frame, bg="black")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Leave>", self.destroy_tooltip)  # Destroy tooltip when mouse leaves canvas

        self.info_text = ScrolledText(main_frame, width=33, fg="black", font=(FONT_NAME, FONT_SIZE))
        self.info_text.grid(row=0, column=1, sticky="ns")

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=20)
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=0)
        btn_frame.grid_columnconfigure(2, weight=0)
        btn_frame.grid_columnconfigure(3, weight=0)
        btn_frame.grid_columnconfigure(4, weight=0)
        btn_frame.grid_columnconfigure(5, weight=0)
        btn_frame.grid_columnconfigure(6, weight=1)

        zoom_buttons = ttk.Frame(btn_frame)
        zoom_buttons.grid(row=0, column=1, padx=20)
        ttk.Button(zoom_buttons, text="Zoom +", command=self.zoom_in).pack(side=tk.LEFT, padx=5)
        ttk.Button(zoom_buttons, text="Zoom -", command=self.zoom_out).pack(side=tk.LEFT, padx=5)

        nav_buttons = ttk.Frame(btn_frame)
        nav_buttons.grid(row=0, column=3, padx=20)
        ttk.Button(nav_buttons, text="Previous", command=self.prev_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(nav_buttons, text="Next", command=self.next_image).pack(side=tk.LEFT, padx=5)

        rotate_buttons = ttk.Frame(btn_frame)
        rotate_buttons.grid(row=0, column=5, padx=20)
        ttk.Button(rotate_buttons, text="Rotate Left", command=self.rotate_left).pack(side=tk.LEFT, padx=5)
        ttk.Button(rotate_buttons, text="Rotate Right", command=self.rotate_right).pack(side=tk.LEFT, padx=5)


        ttk.Button(btn_frame, text="Exit", command=self.win.destroy).grid(row=0, column=6, sticky="e", padx=25)

        self.show_image()

    def center_window(self):
        """Center the window on the screen."""
        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()
        x = (screen_width - WINDOW_WIDTH) // 2
        y = (screen_height - WINDOW_HEIGHT) // 2
        self.win.geometry(f"+{x}+{y}")

    def zoom_in(self):
        """Increase the zoom factor by 20%."""
        self.zoom_factor *= 1.2
        self.show_image()

    def zoom_out(self):
        """Decrease the zoom factor by 20%, with a minimum of 0.1."""
        self.zoom_factor = max(self.zoom_factor / 1.2, 0.1)
        self.show_image()

    def rotate_left(self):
        """Rotate the image 90 degrees counterclockwise."""
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.show_image()

    def rotate_right(self):
        """Rotate the image 90 degrees clockwise."""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.show_image()

    def create_tooltip(self, widget, x, y, text):
        """Create a tooltip at the specified position with the given text."""
        if self.tooltip:
            self.tooltip.destroy()
        self.tooltip = tk.Toplevel(widget)
        self.tooltip.wm_overrideredirect(True)  # Remove window borders
        self.tooltip.wm_geometry(f"+{x+10}+{y+10}")  # Position tooltip near mouse
        label = tk.Label(self.tooltip, text=text, bg="white", fg="black", relief="solid", borderwidth=1, font=(FONT_NAME, 10))
        label.pack()

    def destroy_tooltip(self, event=None):
        """Destroy the tooltip if it exists."""
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def on_mouse_move(self, event):
        """Handle mouse movement to display coordinates in a tooltip."""
        hdu = self.image_hdus[self.index]
        shape = hdu.data.shape
        x = event.x * shape[1] / self.canvas.winfo_width()
        y = shape[0] - (event.y * shape[0] / self.canvas.winfo_height())
        self.last_mouse_pos = (x, y)

        # Destroy existing tooltip
        self.destroy_tooltip()

        # Create tooltip with coordinates after a short delay
        def show_tooltip():
            try:
                wcs = WCS(hdu.header, relax=True)
                ra, dec = wcs.pixel_to_world_values(x, y)
                ctype1 = hdu.header.get('CTYPE1', 'Unknown')
                ctype2 = hdu.header.get('CTYPE2', 'Unknown')
                tooltip_text = f"{ctype1}: {ra:.6f}\n{ctype2}: {dec:.6f}"
            except Exception:
                tooltip_text = f"Pixel X: {x:.2f}\nPixel Y: {y:.2f}"
            self.create_tooltip(self.canvas, event.x_root, event.y_root, tooltip_text)

        self.win.after(100, show_tooltip)  # Delay tooltip creation by 100 ms

    def show_image(self, mouse_x=None, mouse_y=None):
        """Display the current image HDU with zoom, rotation, and static header info."""
        hdu = self.image_hdus[self.index]
        data = hdu.data
        header = hdu.header

        # Debug: Print header to console for inspection
        print(f"FITS Header for HDU #{self.hdul.index(hdu)}:")
        for key, value in header.items():
            if key == 'COMMENT' and isinstance(value, list):
                if all(str(v).startswith("Index(") for v in value):
                    continue  # skip verbose astrometry.net index entries
            print(f"{key}: {value}")

        norm_data = np.nan_to_num(data)
        norm_data = (norm_data - np.min(norm_data)) / (np.ptp(norm_data) + 1e-9)

        fig = plt.figure(figsize=(6 * self.zoom_factor, 6 * self.zoom_factor), dpi=100)
        plt.imshow(np.rot90(norm_data, k=self.rotation_angle // 90), cmap="gray", origin='lower')
        plt.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf)
        photo = ImageTk.PhotoImage(img)

        self.canvas.configure(image=photo)
        self.canvas.image = photo

        # Clear the info text and display basic image information
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, f"HDU #{self.hdul.index(hdu)}\n")
        self.info_text.insert(tk.END, f"Shape: {data.shape}\n")
        self.info_text.insert(tk.END, f"Type: {type(hdu).__name__}\n")
        self.info_text.insert(tk.END, f"Zoom: {self.zoom_factor:.2f}x\n")
        self.info_text.insert(tk.END, f"Rotation: {self.rotation_angle}°\n")

        # Display relevant header entries
        self.info_text.insert(tk.END, "\nFITS Header (Filtered):\n")
        self.info_text.insert(tk.END, "-" * 30 + "\n")
        exclude_prefixes = ['COMMENT', 'HISTORY']
        exclude_exact = ['SIMPLE', 'BITPIX', 'EXTEND']
        for key in header:
            if any(key.startswith(pref) for pref in exclude_prefixes):
                continue
            if key in exclude_exact or key.startswith('NAXIS'):
                continue
            self.info_text.insert(tk.END, f"{key}: {header[key]}\n")

        # Display a few COMMENT and HISTORY entries
        if 'COMMENT' in header:
            for i, comment in enumerate(header['COMMENT'][:5]):  # Limit to 5 comments
                if comment.strip():
                    self.info_text.insert(tk.END, f"COMMENT: {comment}\n")
        if 'HISTORY' in header:
            for i, history in enumerate(header['HISTORY'][:5]):  # Limit to 5 history entries
                if history.strip():
                    self.info_text.insert(tk.END, f"HISTORY: {history}\n")

    def next_image(self):
        """Show the next image HDU."""
        self.index = (self.index + 1) % len(self.image_hdus)
        self.show_image()

    def prev_image(self):
        """Show the previous image HDU."""
        self.index = (self.index - 1) % len(self.image_hdus)
        self.show_image()

    def on_mousewheel(self, event):
        """Handle mouse wheel for image navigation."""
        if event.delta < 0:
            self.next_image()
        elif event.delta > 0:
            self.prev_image()

    def on_mousewheel_linux(self, event):
        """Handle mouse wheel for Linux systems."""
        if event.num == 4:
            self.prev_image()
        elif event.num == 5:
            self.next_image()

# Configuration settings
PAGE_SIZE = 50
WINDOW_WIDTH = 1800
WINDOW_HEIGHT = 950
FONT_SIZE = 10
FONT_NAME = "Consolas"
BG_COLOR = "black"
FG_COLOR = "lime"
DEFAULT_COLUMN_WIDTH = 15
USE_MEMMAP = True

class FITSViewer:
    def __init__(self, root, file_path):
        """Initialize the FITS Viewer for tabular data or fallback message."""
        global USE_MEMMAP
        self.root = root
        self.file_path = file_path  # Store file_path for ImageViewer
        self.root.title("FITS Viewer")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.center_window()

        self.font_size = FONT_SIZE
        self.column_width = DEFAULT_COLUMN_WIDTH
        self.page = 0
        self.page_size = PAGE_SIZE

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")

        try:
            self.hdul = fits.open(file_path, memmap=USE_MEMMAP)
        except ValueError as e:
            if 'BZERO/BSCALE/BLANK' in str(e):
                self.hdul = fits.open(file_path, memmap=False)
                USE_MEMMAP = False
                messagebox.showinfo("Memmap Disabled", "BZERO/BSCALE/BLANK headers detected. Opened without memmap.")
            else:
                raise e

        # Find the first BinTableHDU or TableHDU
        self.EXT = next(
            (i for i, hdu in enumerate(self.hdul) if isinstance(hdu, (fits.BinTableHDU, fits.TableHDU))),
            None
        )

        # Initialize table attributes
        if self.EXT is not None:
            self.header = self.hdul[self.EXT].header
            self.colnames = self.hdul[self.EXT].columns.names
            self.nrows = self.header.get('NAXIS2', 0)
        else:
            self.colnames = []
            self.nrows = 0

        # Set up main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Text output area
        self.text = ScrolledText(
            main_frame,
            font=(FONT_NAME, self.font_size),
            bg=BG_COLOR,
            fg=FG_COLOR
        )
        self.text.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.text.bind("<MouseWheel>", self.on_mousewheel)
        self.text.bind("<Button-4>", self.on_mousewheel_linux)
        self.text.bind("<Button-5>", self.on_mousewheel_linux)

        # Column selection (right)
        col_frame = ttk.Frame(main_frame)
        col_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ns")
        tk.Label(col_frame, text="Columns:").pack()
        self.column_listbox = tk.Listbox(col_frame, selectmode=tk.MULTIPLE, height=40, exportselection=False, width=30)
        self.column_listbox.pack(fill=tk.Y)
        if self.EXT is not None:
            for name in self.colnames:
                self.column_listbox.insert(tk.END, name)
            for i in range(min(10, len(self.colnames))):
                self.column_listbox.select_set(i)
        ttk.Button(col_frame, text="Update Columns", command=self.display_page).pack(pady=5)

        # Rows and Column Width input
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=1, column=0, columnspan=2, pady=5)
        main_frame.columnconfigure(0, weight=1)

        rows_frame = ttk.Frame(input_frame)
        rows_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(rows_frame, text="Rows per Page:").pack(side=tk.LEFT)
        self.rows_entry = ttk.Entry(rows_frame, width=5)
        self.rows_entry.insert(0, str(self.page_size))
        self.rows_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(rows_frame, text="Set Rows", command=self.update_page_size).pack(side=tk.LEFT)

        width_frame = ttk.Frame(input_frame)
        width_frame.pack(side=tk.LEFT, padx=5)
        tk.Label(width_frame, text="Col Width:").pack(side=tk.LEFT)
        self.width_entry = ttk.Entry(width_frame, width=5)
        self.width_entry.insert(0, str(self.column_width))
        self.width_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(width_frame, text="Set Width", command=self.update_column_width).pack(side=tk.LEFT)

        # Controls (centered buttons)
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=5)
        tk.Label(control_frame, text="Jump to page:").grid(row=0, column=0, padx=5)
        self.jump_entry = ttk.Entry(control_frame, width=5)
        self.jump_entry.grid(row=0, column=1, padx=5)
        ttk.Button(control_frame, text="Go", command=self.jump_to_page).grid(row=0, column=2, padx=5)
        ttk.Button(control_frame, text="Previous", command=self.prev_page).grid(row=0, column=3, padx=5)
        ttk.Button(control_frame, text="Next", command=self.next_page).grid(row=0, column=4, padx=5)
        ttk.Button(control_frame, text="A -", command=self.decrease_font).grid(row=0, column=5, padx=5)
        ttk.Button(control_frame, text="A +", command=self.increase_font).grid(row=0, column=6, padx=5)
        control_frame.columnconfigure(7, weight=1)

        # Image Viewer button (bottom left)
        image_frame = ttk.Frame(main_frame)
        image_frame.grid(row=2, column=0, padx=25, pady=5, sticky="w")
        ttk.Button(image_frame, text="Show Image Viewer", command=self.open_image_viewer).pack(side=tk.LEFT)

        # Exit button (bottom right)
        exit_frame = ttk.Frame(main_frame)
        exit_frame.grid(row=2, column=1, padx=25, pady=5, sticky="e")
        ttk.Button(exit_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)

        # Status
        self.status = ttk.Label(self.root, text="")
        self.status.pack()

        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        # Display initial content
        self.display_page()

    def center_window(self):
        """Center the window on the screen."""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - WINDOW_WIDTH) // 2
        y = (screen_height - WINDOW_HEIGHT) // 2
        self.root.geometry(f"+{x}+{y}")

    def get_selected_columns(self):
        """Get the list of selected column names."""
        indices = self.column_listbox.curselection()
        return [self.colnames[i] for i in indices] if indices else self.colnames[:10]

    def display_page(self):
        """Display the current page of tabular data or a message if no table data exists."""
        self.text.config(state='normal')
        self.text.delete("1.0", tk.END)

        if self.EXT is None:
            self.text.insert(tk.END, "No table data found, check Image Viewer.\n")
            self.status.config(text="No table data available")
            self.text.config(state='disabled')
            return

        start = self.page * self.page_size
        end = min(start + self.page_size, self.nrows)
        columns = self.get_selected_columns()

        header = "".join(name.ljust(self.column_width) for name in columns)
        self.text.insert(tk.END, header + "\n")
        self.text.insert(tk.END, "-" * len(header) + "\n")

        data = self.hdul[self.EXT].data[start:end]
        for row in data:
            vals = [
                str(row[name])[:self.column_width - 1].ljust(self.column_width) if not isinstance(row[name], (np.floating, np.integer)) or not np.isnan(row[name])
                else "NaN".ljust(self.column_width) for name in columns
            ]
            self.text.insert(tk.END, "".join(vals) + "\n")

        self.text.config(state='disabled')
        self.status.config(text=f"Page {self.page + 1} of {int(self.nrows / self.page_size) + 1}, Total Rows: {self.nrows}, Displayed: {end - start}")

    def next_page(self):
        """Navigate to the next page of tabular data."""
        if self.EXT is None:
            return
        if (self.page + 1) * self.page_size < self.nrows:
            self.page += 1
            self.display_page()

    def prev_page(self):
        """Navigate to the previous page of tabular data."""
        if self.EXT is None:
            return
        if self.page > 0:
            self.page -= 1
            self.display_page()

    def on_mousewheel(self, event):
        """Handle mouse wheel for page navigation."""
        if self.EXT is None:
            return
        if event.delta < 0:
            self.next_page()
        elif event.delta > 0:
            self.prev_page()

    def on_mousewheel_linux(self, event):
        """Handle mouse wheel for Linux systems."""
        if self.EXT is None:
            return
        if event.num == 4:
            self.prev_page()
        elif event.num == 5:
            self.next_page()

    def increase_font(self):
        """Increase the font size of the text area."""
        if self.EXT is None:
            return
        self.font_size += 1
        self.text.configure(font=(FONT_NAME, self.font_size))

    def decrease_font(self):
        """Decrease the font size of the text area."""
        if self.EXT is None:
            return
        if self.font_size > 6:
            self.font_size -= 1
            self.text.configure(font=(FONT_NAME, self.font_size))

    def update_column_width(self):
        """Update the column width and refresh the display."""
        if self.EXT is None:
            return
        try:
            new_width = int(self.width_entry.get())
            if new_width > 2:
                self.column_width = new_width
                self.display_page()
        except ValueError:
            self.status.config(text="Invalid column width")

    def update_page_size(self):
        """Update the number of rows per page and refresh the display."""
        if self.EXT is None:
            return
        try:
            new_size = int(self.rows_entry.get())
            if new_size > 0 and new_size <= 1000:
                self.page_size = new_size
                self.page = 0
                self.display_page()
                self.status.config(text=f"Page 1 of {int(self.nrows / self.page_size) + 1}, Total Rows: {self.nrows}")
        except ValueError:
            self.status.config(text="Invalid number of rows")

    def jump_to_page(self):
        """Jump to a specific page of tabular data."""
        if self.EXT is None:
            return
        try:
            page_num = int(self.jump_entry.get()) - 1
            max_page = int(self.nrows / self.page_size)
            if 0 <= page_num <= max_page:
                self.page = page_num
                self.display_page()
            else:
                self.status.config(text=f"Page must be between 1 and {max_page + 1}")
        except ValueError:
            self.status.config(text="Invalid page number")

    def open_image_viewer(self):
        """Open the Image Viewer for image HDUs."""
        ImageViewer(self.file_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: py fits_browser.py <fits_file_path>")
        sys.exit(1)
    file_path = sys.argv[1]
    root = tk.Tk()
    try:
        app = FITSViewer(root, file_path)
        root.mainloop()
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
