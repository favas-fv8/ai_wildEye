# AI WildEye — Wildlife Image Recognition Project

A computer-vision project combining a Django application with a TensorFlow-based machine-learning workflow for image-oriented wildlife recognition and experimentation.

## Overview

The repository contains an application project, machine-learning code, supporting resources, installation scripts, and a generated viva/documentation utility. Large training data and runtime archives are intentionally excluded through `.gitignore`.

## Technology Stack

- **Backend:** Django 4
- **Machine Learning:** TensorFlow CPU, NumPy, pandas, SciPy
- **Computer Vision:** OpenCV, Pillow
- **Visualization:** Matplotlib
- **Utilities:** Requests, playsound
- **Runtime:** Python

## Repository Structure

```text
ai_wildEye/
├── ml_code/               # Machine-learning code and training resources
├── project/               # Django application
├── res/                   # Supporting resources / runtime assets
├── generate_viva_pdf.py   # Generate project viva documentation
├── install.bat            # Windows installation helper
├── install_uv.bat         # Alternative installation helper
├── run.bat                # Windows run helper
├── requirements.txt       # Python dependencies
└── .gitignore             # Excludes generated/runtime and large data
```

## Installation

Create a Python virtual environment and install the dependencies:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Windows users can also review the included installation scripts.

## Data & Large Files

The repository excludes large ML training data, archives, generated Django runtime files, and FFmpeg-related artifacts from version control. If the application requires one of these resources, provide it locally according to the project structure before running the workflow.

## Development Notes

This repository is organized as an application/ML project rather than a minimal library package. The exact model workflow and supported wildlife classes should be reviewed in `ml_code/` before deployment or reuse.

## Disclaimer

This project is intended for educational and research purposes. Model predictions should not be treated as definitive identification without appropriate human review.

## License

No license file is currently defined in the repository. Please contact the repository owner for reuse or licensing questions.
