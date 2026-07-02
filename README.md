# EIS Impedance Plotter

Python tools for generating publication-style Electrochemical Impedance Spectroscopy (EIS) plots from Excel or CSV spreadsheet data.

The main script is `auto_impedance_plots.py`. It reads impedance data from Excel or CSV files, detects repeated 5-column impedance blocks, and creates combined comparison plots for all samples.

The project also includes an older interactive helper script, `plot_csv.py`, for making a simple plot from selected CSV columns.

## Features

`auto_impedance_plots.py` can:

* Read `.xlsx`, `.xls`, and `.csv` files
* Detect repeated 5-column impedance blocks automatically
* Use sample names from the sheet as legend labels
* Create combined comparison plots with each sample in a different color
* Plot fitted data as solid lines
* Plot raw/unfitted data as hollow markers
* Match fitted and raw data by sample name using the same color
* Save plots to an output folder
* Use a custom base name for output filenames with `--name`
* Create normal, log-scale, and zoomed Nyquist plots
* Create Bode magnitude and phase plots
* Use publication-style formatting:

  * Times New Roman font
  * square graph area
  * no titles
  * no gridlines
  * inward ticks on all sides
  * thicker axis borders
* Add scientific scaling directly into Nyquist axis labels
* Use impedance units as `Ω/cm²`
* Use frequency labels as `log F (Hz)`
* Control raw marker size with `--marker-size`
* Control fitted line width with `--line-width`
* Override axis labels for specific plots
* Export cleaned computed data with `--cleaned-csv`
* Print debug information for header matching with `--debug-headers`

## Expected Data Format

The impedance script expects repeated blocks across the spreadsheet. Each block is usually 5 columns wide:

```text
Freq    Z' (a)    Z'' (b)    Z or Mag    teta or Phase
```

The first row of each block can contain the sample name. The second row should contain the headers. Data starts on the third row.

Example layout:

```text
0.001NP
Freq    Z' (a)    Z'' (b)    Z    teta
...
```

The script accepts flexible impedance magnitude headers such as:

```text
Z
|Z|
Z (ohm)
Z/ohm
Mag
Magnitude
Mod Z
Zmod
Abs Z
Impedance
Impedance Magnitude
```

It also accepts flexible theta/phase headers such as:

```text
teta
theta
θ
phase
```

## Output Plots

The script creates five PNG files:

1. Normal Nyquist plot: `-Z'' vs Z'`
2. Log-scale Nyquist plot: `-Z'' vs Z'` with log x/y axes
3. Zoomed Nyquist plot: `-Z'' vs Z'` with extreme outliers ignored for axis limits
4. Bode magnitude plot: `log Z vs log F`
5. Phase plot: `-theta vs log F`

The log-scale Nyquist plot only includes rows where both `Z'` and `-Z''` are positive.

With a custom name such as `"10 days"`, the output files are:

```text
plots/10_days_zpp_vs_zp.png
plots/10_days_zpp_vs_zp_logscale.png
plots/10_days_zpp_vs_zp_zoomed.png
plots/10_days_logz_vs_logf.png
plots/10_days_theta_vs_logf.png
```

## Plot Style

The generated figures use a publication-style format:

* Times New Roman font
* 16 pt axis and tick labels
* no plot titles
* no gridlines
* square graph/axis area
* rectangular output image when needed to include the legend
* inward ticks
* ticks on all four sides
* thicker axis spines
* legend outside the graph area when many samples are present
* high-resolution PNG output using `dpi=300`

The graph panel itself is square, while the saved image may be rectangular so the legend can fit outside the graph.

## Axis Label Defaults

Default axis labels are formatted using parentheses for units.

### Normal and Zoomed Nyquist Plots

If no scientific scaling is needed:

```text
Z' (Ω/cm²)
-Z'' (Ω/cm²)
```

If scientific scaling is needed:

```text
Z' × 10^x (Ω/cm²)
-Z'' × 10^y (Ω/cm²)
```

The tick labels are manually scaled so Matplotlib does not show offset text like `1e9` or `1e10`.

### Log-Scale Nyquist Plot

```text
Z' (Ω/cm²)
-Z'' (Ω/cm²)
```

### Bode Magnitude Plot

```text
log F (Hz)
log |Z| (Ω/cm²)
```

### Phase Plot

```text
log F (Hz)
-θ (degrees)
```

## Clone and Run on a Local Machine

First make sure Python and Git are installed.

Clone this repository:

```bash
git clone https://github.com/chrislleung/eis-impedance-plotter.git
cd eis-impedance-plotter
```

Create and activate a virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

On macOS or Linux, activate it with:

```bash
source .venv/bin/activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

Put your Excel or CSV data files in the project folder, or in a folder such as `data/`.

## Main Commands

### One-File Workflow

Use this when you only have one impedance file:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days"
```

This creates all five output plots from one file.

### Two-File Fit vs Raw Workflow

Use this when you have one fitted-data file and one raw/before-fitting file:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

In this workflow:

* fitted data is plotted as solid lines
* raw/unfitted data is plotted as hollow markers
* matching samples use the same color

### Fit-Only Workflow

Use this when you only want to plot fitted data:

```bash
python auto_impedance_plots.py --fit-file data/10days.xlsx --out plots --name "10 days fit"
```

### Raw-Only Workflow

Use this when you only want to plot raw/unfitted data:

```bash
python auto_impedance_plots.py --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days raw"
```

## Command Extensions and Options

Add these options to the main command when needed.

### Output Folder

Use `--out` to choose where the plots are saved.

```text
--out plots
```

Example output folder:

```text
plots/
```

### Custom Output Name

Use `--name` to customize the output filenames.

```text
--name "10 days"
```

This turns into filenames such as:

```text
10_days_zpp_vs_zp.png
10_days_logz_vs_logf.png
```

### Excel Sheet Selection

Use `--sheet` to choose a specific Excel sheet.

```text
--sheet Sheet1
```

### Cleaned CSV Export

Use `--cleaned-csv` to save the cleaned computed data.

```text
--cleaned-csv
```

This creates:

```text
plots/combined_cleaned_impedance_data.csv
```

The cleaned CSV includes columns such as:

```text
sample
source_type
freq
z_prime
z_double_prime
z
theta
log_freq
log_z
neg_z_double_prime
neg_theta
```

The `source_type` column indicates whether the row came from fitted data or raw data.

### Debug Header Detection

Use `--debug-headers` if blocks are skipped or headers are not recognized.

```text
--debug-headers
```

This prints each possible block's raw headers, normalized headers, and detected column type.

### Zoom Percentile

Use `--zoom-percentile` to control the zoomed Nyquist plot.

```text
--zoom-percentile 85
```

Common values:

```text
--zoom-percentile 80
--zoom-percentile 85
--zoom-percentile 90
--zoom-percentile 95
```

Lower values zoom in more. Higher values zoom out more.

### Raw Marker Size

Use `--marker-size` to control the size of hollow raw-data markers.

```text
--marker-size 12
```

Common values:

```text
--marker-size 20
--marker-size 15
--marker-size 12
--marker-size 10
--marker-size 8
```

### Fitted Line Width

Use `--line-width` to control the thickness of fitted-data lines.

```text
--line-width 1.2
```

Common values:

```text
--line-width 1.5
--line-width 1.2
--line-width 1.0
--line-width 0.8
```

## Custom Axis Labels

The script supports custom axis labels for each graph.

Only the specified graph is changed. All other graphs keep the default labels.

### Normal Nyquist Plot

Use these options to override the normal Nyquist labels:

```text
--xlabel-zpp-vs-zp "Custom X Label"
--ylabel-zpp-vs-zp "Custom Y Label"
```

Example:

```text
--xlabel-zpp-vs-zp "Real Impedance"
--ylabel-zpp-vs-zp "Imaginary Impedance"
```

### Log-Scale Nyquist Plot

Use these options to override the log-scale Nyquist labels:

```text
--xlabel-zpp-vs-zp-logscale "Custom X Label"
--ylabel-zpp-vs-zp-logscale "Custom Y Label"
```

Example:

```text
--xlabel-zpp-vs-zp-logscale "Z' (Ω/cm²)"
--ylabel-zpp-vs-zp-logscale "-Z'' (Ω/cm²)"
```

### Zoomed Nyquist Plot

Use these options to override the zoomed Nyquist labels:

```text
--xlabel-zpp-vs-zp-zoomed "Custom X Label"
--ylabel-zpp-vs-zp-zoomed "Custom Y Label"
```

Example:

```text
--xlabel-zpp-vs-zp-zoomed "Z' (Ω/cm²)"
--ylabel-zpp-vs-zp-zoomed "-Z'' (Ω/cm²)"
```

### Bode Magnitude Plot

Use these options to override the `log Z vs log F` labels:

```text
--xlabel-logz-vs-logf "Custom X Label"
--ylabel-logz-vs-logf "Custom Y Label"
```

Example:

```text
--xlabel-logz-vs-logf "log F (Hz)"
--ylabel-logz-vs-logf "log |Z| (Ω/cm²)"
```

### Phase Plot

Use these options to override the `-theta vs log F` labels:

```text
--xlabel-theta-vs-logf "Custom X Label"
--ylabel-theta-vs-logf "Custom Y Label"
```

Example:

```text
--xlabel-theta-vs-logf "log F (Hz)"
--ylabel-theta-vs-logf "-θ (degrees)"
```

## Recommended Commands

### Recommended One-File Command

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days"
```

Optional extensions:

```text
--zoom-percentile 85
--cleaned-csv
--debug-headers
--sheet Sheet1
```

### Recommended Two-File Command

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Optional extensions:

```text
--marker-size 12
--line-width 1.0
--zoom-percentile 85
--cleaned-csv
--debug-headers
--sheet Sheet1
```

### Recommended Two-File Command for Cleaner Figures

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days" --marker-size 10 --line-width 1.0 --zoom-percentile 85
```

Optional extensions:

```text
--cleaned-csv
--debug-headers
--sheet Sheet1
```

## Example Custom Label Commands

### Custom Bode Magnitude Labels

Command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add these extensions:

```text
--xlabel-logz-vs-logf "log F (Hz)"
--ylabel-logz-vs-logf "log |Z| (Ω/cm²)"
```

### Custom Phase Labels

Command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add these extensions:

```text
--xlabel-theta-vs-logf "log F (Hz)"
--ylabel-theta-vs-logf "-θ (degrees)"
```

### Custom Normal Nyquist Labels

Command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add these extensions:

```text
--xlabel-zpp-vs-zp "Z' (Ω/cm²)"
--ylabel-zpp-vs-zp "-Z'' (Ω/cm²)"
```

### Custom Zoomed Nyquist Labels

Command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add these extensions:

```text
--xlabel-zpp-vs-zp-zoomed "Z' (Ω/cm²)"
--ylabel-zpp-vs-zp-zoomed "-Z'' (Ω/cm²)"
```

### Custom Log-Scale Nyquist Labels

Command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add these extensions:

```text
--xlabel-zpp-vs-zp-logscale "Z' (Ω/cm²)"
--ylabel-zpp-vs-zp-logscale "-Z'' (Ω/cm²)"
```

## Custom Axis Ranges

The script supports custom axis display ranges for each graph. These options change only the visible axis limits; they do not delete or modify the underlying data.

Range values use this format:

```text
"min,max"
```

Use `inf` or `-inf` when you want one side of the axis to remain automatic.

Examples:

```text
"0,inf"       show values from 0 to the automatic upper limit
"-inf,100"    show values from the automatic lower limit to 100
"0,100000"    show values from 0 to 100000
"-20,80"      show values from -20 to 80
"1e3,1e9"     show values from 1000 to 1000000000
```

### Normal Nyquist Plot Ranges

Use these options to control the normal `-Z'' vs Z'` plot:

```text
--xrange-zpp-vs-zp "min,max"
--yrange-zpp-vs-zp "min,max"
```

Examples:

```text
--xrange-zpp-vs-zp "0,inf"
--yrange-zpp-vs-zp "0,inf"
--xrange-zpp-vs-zp "0,100000"
--yrange-zpp-vs-zp "0,50000"
```

### Log-Scale Nyquist Plot Ranges

Use these options to control the log-scale `-Z'' vs Z'` plot:

```text
--xrange-zpp-vs-zp-logscale "min,max"
--yrange-zpp-vs-zp-logscale "min,max"
```

Examples:

```text
--xrange-zpp-vs-zp-logscale "1,1e9"
--yrange-zpp-vs-zp-logscale "1,1e10"
```

For log-scale plots, axis limits must be positive. Values of `0` or negative values are not valid on log axes.

### Zoomed Nyquist Plot Ranges

Use these options to control the zoomed `-Z'' vs Z'` plot:

```text
--xrange-zpp-vs-zp-zoomed "min,max"
--yrange-zpp-vs-zp-zoomed "min,max"
```

Examples:

```text
--xrange-zpp-vs-zp-zoomed "0,100000"
--yrange-zpp-vs-zp-zoomed "0,50000"
```

If custom ranges are provided for the zoomed plot, they override the automatic `--zoom-percentile` display limits.

### Bode Magnitude Plot Ranges

Use these options to control the `log |Z| vs log F` plot:

```text
--xrange-logz-vs-logf "min,max"
--yrange-logz-vs-logf "min,max"
```

Examples:

```text
--xrange-logz-vs-logf "0,6"
--yrange-logz-vs-logf "0,10"
```

### Phase Plot Ranges

Use these options to control the `-θ vs log F` plot:

```text
--xrange-theta-vs-logf "min,max"
--yrange-theta-vs-logf "min,max"
```

Examples:

```text
--xrange-theta-vs-logf "0,6"
--yrange-theta-vs-logf "-20,80"
```

### Example: Show Only Positive Nyquist Values

Base command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add these extensions:

```text
--xrange-zpp-vs-zp "0,inf"
--yrange-zpp-vs-zp "0,inf"
```

### Example: Manually Set the Zoomed Nyquist Window

Base command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add these extensions:

```text
--xrange-zpp-vs-zp-zoomed "0,100000"
--yrange-zpp-vs-zp-zoomed "0,50000"
```

### Example: Limit the Phase Plot Range

Base command:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Add this extension:

```text
--yrange-theta-vs-logf "-20,80"
```


## Generic CSV Plotter

The project also includes `plot_csv.py`, an interactive script for simple CSV plots.

Run it with:

```bash
python plot_csv.py
```

It asks for:

* CSV file path
* x-axis column
* y-axis column
* graph type
* whether to save the result as an image

This script is separate from the EIS-specific plotting workflow.

## Troubleshooting

### Missing Excel Dependency

If reading `.xlsx` files fails with an `openpyxl` error, install the project requirements:

```bash
pip install -r requirements.txt
```

### File Not Found

Check that the file path is written exactly as it appears in the `data/` folder.

For example, if the filename contains a space:

```text
10days-before fitting.xlsx
```

use quotes:

```bash
python auto_impedance_plots.py --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days raw"
```

Make sure there is no accidental space after the opening quote:

```text
"data/10days-before fitting.xlsx"     correct
" data/10days-before fitting.xlsx"    incorrect
```

### No Impedance Blocks Found

Use `--debug-headers` to see how the script is reading the headers:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --debug-headers
```

Check that each block has headers for:

* frequency
* `Z'`
* `Z''`
* magnitude `Z`
* theta or phase

### Small Samples Are Hard to See

Use the log-scale or zoomed Nyquist output:

```text
*_zpp_vs_zp_logscale.png
*_zpp_vs_zp_zoomed.png
```

Large impedance samples can make smaller samples appear compressed near the origin in the normal Nyquist plot.

### Raw Markers Are Too Large

Use a smaller marker size:

```bash
python auto_impedance_plots.py --fit-file data/fitted.xlsx --raw-file data/raw.xlsx --out plots --name "comparison" --marker-size 10
```

### Legend Makes the Image Rectangular

This is expected. The graph panel itself is square, but the saved PNG may be rectangular so the legend can fit outside the plot area.
