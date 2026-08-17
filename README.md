# KabuKids

KabuKids is a Python application built with Kivy. This project includes a desktop UI and several supporting modules for the app flow.

## Requirements

- Python 3.10 or newer
- A terminal or command prompt
- Internet access to install the required Python packages

## Install dependencies

From the project folder, run:

```bash
pip install -r requirements.txt
```

> Note: The dependency file in this project is named `requirements.txt` (singular), not `requirements.txt`.

## Run the application

Once the dependencies are installed, start the app with:

```bash
python app_main.py
```

## Project structure

- `app_main.py` - main app entry point
- `KabuKids.kv` - Kivy screen layout definitions
- `screens/` - app screens and logic
- `widgets/` - reusable UI components
- `requirements.txt` - Python package list

## Notes

This project may require additional OS-level dependencies depending on the environment, especially for audio and ML-related packages. If you run into installation issues, install the packages in the order shown in the dependency file or use a clean virtual environment.
