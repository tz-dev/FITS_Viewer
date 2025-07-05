# FITS Viewer

A lightweight tool for viewing and navigating FITS (Flexible Image Transport System) files, built with Python and Tkinter. This tool dynamically loads and displays tabular data from FITS files, especially suited for large datasets like `specObj-dr17.fits` from the SDSS.

## Features

- **Dynamic Loading:** Columns are automatically loaded from the FITS file, with no hardcoded columns in the code.
- **Navigation:** Previous/Next page with mouse or buttons.
- **Jump to:** Jump to any page for quicker navigation.
- **Mousewheel Support:** Navigate pages via scroll wheel.
- **Customization:** Adjust font size, column width, rows & columns to display.
- **Status:** Shows current page, total rows, and displayed rows.
- **Memory-Efficient:** Uses `memmap=True` to handle large files.

![FITS Viewer Screenshot](img/screenshot.png)

---

## Prerequisites

- **Python 3.x** – Must be installed and in the system PATH (check via `python --version`)
- **Dependencies** (install via `pip`):

```bash
  pip install astropy numpy
```

---

## Installation

**Clone the repository or download the files**:
```bash
   git clone https://github.com/tz-dev/FITS_Viewer.git
   cd FITS_Viewer
```
Ensure fits_browser.py and fview.bat are in the same directory.

---

## Calling via Batch Script

Use the provided fview.bat to run the tool with a FITS file:
```bash
fview "path\to\your\file.fits"
```
## Calling via Python

Run the script directly with Python:
```bash
python fits_viewer.py "path\to\your\file.fits"
```
