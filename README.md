🔋 Battery Capacity Tool

GUI application for calculating discharged battery capacity from CSV files exported from Keysight N6705C / PathWave App Suite.

The application:

Calculates battery capacity up to a specified voltage cutoff

Plots I(t) and V(t) graphs

Saves the plot as PNG

Allows setting Battery ID

Supports large CSV files

📌 Features

Capacity calculation using numerical integration:

𝑄 = ∫𝐼(𝑡)𝑑𝑡

Voltage cutoff handling (default: 2.7 V)

Linear interpolation at the cutoff crossing

Supports CSV separators:

,

\t

;

Automatic Battery ID detection from filename

Graph generation:

Current vs Time

Voltage vs Time

Automatic PNG export

📂 Expected CSV Format

CSV must be exported from N6705C and contain:

Column	Description
1	Time (s)
3	Voltage (V)
5	Current (A)

The first 4 lines of the file are automatically skipped.

🖥️ Running with Python
1️⃣ Install dependencies
pip install pandas numpy matplotlib


Tkinter is included in standard Python installations.

2️⃣ Run the program
python capacity_gui.py

🧮 Calculation Method

Time, voltage, and current are read from the CSV

Current is integrated using the trapezoidal method

Integration continues while:

Voltage >= Cutoff Voltage


If cutoff is crossed between two samples, linear interpolation is applied

The result is displayed in:

Ah

mAh

Cutoff time

📊 Output

After calculation:

A plot window opens

A PNG file is saved:

BatteryID_I_V_plot.png

🏗️ Building as .exe
Install PyInstaller
pip install pyinstaller

Build command
pyinstaller --onefile --windowed ^
--hidden-import=matplotlib.backends.backend_tkagg ^
--hidden-import=tkinter ^
capacity_gui.py


The executable will be created in:

dist/capacity_gui.exe

⚙️ GUI Parameters
Field	Description
CSV file	Select CSV file
Cutoff voltage	Voltage cutoff value
Battery ID	Battery identifier
Use abs(current)	Use absolute current for integration
🧠 Notes

Graphs are plotted only up to cutoff time

For large files, display downsampling is applied (calculation remains full precision)

Computation runs in a background thread (GUI remains responsive)

🚀 Possible Improvements

Export trimmed CSV up to cutoff

PDF report export

Energy calculation (Wh)

Batch processing

Embedded matplotlib plot inside GUI window

📜 License

MIT License (or adjust as needed)

If you’d like, I can also provide:

A more engineering-focused README (for development teams)

A more user-friendly version (for internal test teams)

A technical methodology section suitable for validation reports
