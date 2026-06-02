# MRI Reconstruction and Analysis

A FastAPI web application for reconstructing MRI slices from k-space data, visualizing frequency information, and applying image post-processing filters.

The browser interface lets you select an H5 file, choose a slice, configure undersampling and filters, then run the complete pipeline. Generated images and a radial frequency-energy graph are displayed in the dashboard.

## Features

### Module 1: MRI Reconstruction

- Loads multi-coil k-space data from an H5 file.
- Applies optional undersampling.
- Reconstructs each coil image with a 2D inverse FFT and FFT shift.
- Combines coil images using root sum of squares (RSS).
- Displays the reconstructed MRI slice and the ground-truth RSS image.

### Module 2: Frequency Analysis

- Generates a sampled k-space visualization.
- Calculates and displays the 2D FFT frequency spectrum.
- Plots a normalized radial frequency-energy profile from low to high frequencies.

### Module 3: Post-Processing

- Noise removal: `gaussian`, `median`, or `none`.
- Smoothing: `blur`, `bilateral`, or `none`.
- Contrast enhancement: `clahe`, `histogram_equalization`, or `none`.

## Requirements

- Python 3.10 or newer
- An H5 MRI dataset with:
  - `kspace`: multi-coil k-space data with shape `(slices, coils, height, width)`
  - `reconstruction_rss`: ground-truth RSS images with shape `(slices, height, width)`

Place compatible `.h5` files in the project root. The default file is:

```text
2022061006_FLAIR01.h5
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the development server:

```powershell
python -m uvicorn app:app --reload
```

Open the dashboard at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Using the Dashboard

1. Select an H5 file from the dropdown.
2. Choose a slice ID.
3. Set the acceleration and center fraction for undersampling.
4. Select the post-processing filters.
5. Click **Run MRI Pipeline**.

Before the first run, image cards display a prompt instead of broken image placeholders. Generated PNG files are written to `outputs/`.

## API

Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Check whether the API is running. |
| `GET` | `/api/info?file_path=<name>.h5` | Read metadata for an H5 file. |
| `GET` | `/api/h5-files` | List H5 files available in the project root. |
| `POST` | `/api/analyze` | Run reconstruction, analysis, and post-processing. |
| `GET` | `/api/files/{filename}` | Retrieve a generated PNG output. |

Example analysis request:

```json
{
  "file_path": "2022061006_FLAIR01.h5",
  "slice_id": 5,
  "acceleration": 2,
  "center_fraction": 0.08,
  "noise_removal": "gaussian",
  "smoothing": "bilateral",
  "contrast_enhancement": "clahe"
}
```

Example request with PowerShell:

```powershell
$body = @{
  file_path = "2022061006_FLAIR01.h5"
  slice_id = 5
  acceleration = 2
  center_fraction = 0.08
  noise_removal = "gaussian"
  smoothing = "bilateral"
  contrast_enhancement = "clahe"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/analyze" `
  -ContentType "application/json" `
  -Body $body
```

## Project Structure

```text
.
|-- app.py               # FastAPI routes and static file server
|-- mri_pipeline.py      # MRI reconstruction and image-processing logic
|-- requirements.txt     # Python dependencies
|-- static/
|   |-- index.html       # Dashboard markup
|   |-- main.js          # Browser-side API calls and rendering
|   `-- style.css        # Dashboard styles
|-- outputs/             # Generated PNG images, ignored by Git
`-- test.py              # Separate tumor-mask visualization utility
```

## Additional Visualization Script

`test.py` is independent from the web pipeline. It expects an H5 file named `volume_100_slice_108.h5` with `image` and `mask` datasets, then opens a Matplotlib window containing MRI modalities, tumor masks, and an overlay.

Run it with:

```powershell
python test.py
```

## Notes

- Input file paths can be relative to the project root.
- Generated files in `outputs/` are ignored by Git.
- This project is intended for analysis and educational use, not clinical diagnosis.
