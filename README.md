# FITS Viewer
A lightweight tool for viewing and navigating FITS (Flexible Image Transport System) files, built with Python and Tkinter. This tool dynamically loads and displays tabular data from FITS files, especially suited for large datasets like `specObj-dr17.fits` from the SDSS.
## Features
- **Dynamic Loading:** Columns are automatically loaded from the FITS file, with no hardcoded columns in the code.
- **Paged Display:** Adjustable number of rows per page (default: 50).
- **Column Selection:** Select any columns to display.
- **Navigation:** Previous/Next page with mouse or buttons.
- **Customization:** Adjust font size and column width.
- **Status:** Shows current page, total rows, and displayed rows.

## Prerequisites
- **Python 3.x:** Must be installed and in the system PATH (check with `python --version`).
- **Dependencies:**
  - `astropy` (for FITS support)
  - `numpy` (for data processing)
  - `tkinter` (for the GUI, typically included with Python)

Install the dependencies with:
```bash
pip install astropy numpy
