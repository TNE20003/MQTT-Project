# MQTT-Project

A Python robot simulation with sensors, an MQTT controller, and a Tkinter window for viewing and publishing MQTT messages.

## Requirements

This project was developed using **Python 3.14**. Install Python 3.14 with pip and Tkinter support. A desktop environment is required for the message viewer.

The application needs network access to the MQTT broker configured in `IO/MQTT_Server.py` (`rule28.i4t.swin.edu.au`). Check the broker address and credentials in that file before running if you need to use a different broker. The MQTT topic prefix is also defined there and used by `IO/UI.py`.

## Install dependencies

Open a terminal in the project root (the folder containing `main.py` and `requirements.txt`). Creating a virtual environment keeps the project dependencies separate from other Python projects.

On Windows (PowerShell):

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If PowerShell blocks the activation script, you can install and run directly with the virtual environment's Python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Tkinter is supplied by your Python installation rather than `requirements.txt`. If `import tkinter` fails, install the Tkinter package appropriate for your operating system and Python version.

## Run the application

With the virtual environment activated, run this command from the project root:

```bash
python main.py
```

This starts the robot with five simulated sensors (light, temperature, distance, pressure, and humidity), runs the controller, and opens the MQTT Message Viewer. The robot and controller connect to the configured broker during startup.

In the viewer, click **Connect** to connect its own MQTT client. Subscribe to `#` to view all messages under the project's topic prefix, or enter a specific topic. The viewer adds the prefix automatically.

Press **Ctrl+C** in the terminal to stop the controller and shut down the robot, then close the viewer window if it is still open.

To launch only the MQTT Message Viewer, run:

```bash
python -m IO.UI
```
