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
* Control raw marker size with `--marker-size`
* Control fitted line width with `--line-width`
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

## Basic One-File Usage

Run the impedance plotter from the project folder:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots
```

This saves the default combined plot files:

```text
plots/combined_zpp_vs_zp.png
plots/combined_zpp_vs_zp_logscale.png
plots/combined_zpp_vs_zp_zoomed.png
plots/combined_logz_vs_logf.png
plots/combined_theta_vs_logf.png
```

## Custom Plot Name

Use `--name` to customize output filenames:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days"
```

This saves:

```text
plots/10_days_zpp_vs_zp.png
plots/10_days_zpp_vs_zp_logscale.png
plots/10_days_zpp_vs_zp_zoomed.png
plots/10_days_logz_vs_logf.png
plots/10_days_theta_vs_logf.png
```

The `--name` value is converted into a safe filename by making it lowercase, replacing spaces with underscores, and removing unsafe filename characters.

## Two-File Fit vs Raw Workflow

The script can also compare two files:

* one fitted-data file
* one raw/unfitted-data file

In this workflow:

* fitted data is plotted as solid lines
* raw/unfitted data is plotted as hollow markers
* matching samples use the same color

Example:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

This creates the same five output plots, but fitted and raw data are shown together for comparison.

## One File as Fit or Raw Only

You can also provide only a fitted file:

```bash
python auto_impedance_plots.py --fit-file data/10days.xlsx --out plots --name "10 days fit"
```

Or only a raw/unfitted file:

```bash
python auto_impedance_plots.py --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days raw"
```

## Marker and Line Controls

Raw/unfitted data is plotted using hollow markers. To make the hollow markers smaller or larger, use `--marker-size`:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days" --marker-size 18
```

Try smaller values if the markers are too large:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days" --marker-size 12
```

Fitted data is plotted using solid lines. To adjust line thickness, use `--line-width`:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days" --line-width 1.2
```

## Zoom Control

The zoomed Nyquist plot uses percentile-based axis limits. The default is `90`, which means the largest 10 percent of values are ignored when setting the zoomed axis range.

Change it with:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --zoom-percentile 85
```

## Scientific Axis Labels

For the normal and zoomed Nyquist plots, the script can move scientific scaling into the axis label instead of showing Matplotlib offset text like `1e9` or `1e10`.

For example, instead of showing:

```text
1e9
Z' / Ω
```

the axis label is formatted like:

```text
Z' × 10^9 / Ω
```

The tick labels are scaled manually, so they appear as simple values such as:

```text
0, 2, 4, 6, 8
```

rather than:

```text
0, 2e9, 4e9, 6e9, 8e9
```

This formatting is mainly applied to the normal and zoomed Nyquist plots. The already-logarithmic plots keep their regular labels:

```text
log f
log |Z|
-theta / degrees
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

## Excel Sheet Selection

For Excel files, the first sheet is used by default. To choose a sheet:

```bash
python auto_impedance_plots.py data/10days.xlsx --sheet Sheet1 --out plots
```

This also works in two-file mode:

```bash
python auto_impedance_plots.py --fit-file data/fitted.xlsx --raw-file data/raw.xlsx --sheet Sheet1 --out plots --name "10 days"
```

## Cleaned CSV Export

Use `--cleaned-csv` to save the cleaned computed data:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --cleaned-csv
```

For two-file mode:

```bash
python auto_impedance_plots.py --fit-file data/fitted.xlsx --raw-file data/raw.xlsx --out plots --name "10 days" --cleaned-csv
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

The `source_type` column indicates whether a row came from fitted data or raw data.

## Debug Header Detection

If blocks are skipped because a header is not recognized, run with:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --debug-headers
```

This prints each possible block's raw headers, normalized headers, and detected column type.

For two-file mode:

```bash
python auto_impedance_plots.py --fit-file data/fitted.xlsx --raw-file data/raw.xlsx --out plots --debug-headers
```

This is useful when a spreadsheet uses unusual column names.

## Common Commands

Basic one-file run:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots
```

Run with custom name:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days"
```

Run with fitted and raw files:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days"
```

Run with smaller raw markers:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days" --marker-size 12
```

Run with a different fitted line width:

```bash
python auto_impedance_plots.py --fit-file "data/10days.xlsx" --raw-file "data/10days-before fitting.xlsx" --out plots --name "10 days" --line-width 1.2
```

Run with a different zoom percentile:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --zoom-percentile 85
```

Run with cleaned CSV export:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --cleaned-csv
```

Run with debug header output:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --debug-headers
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

### Missing Excel dependency

If reading `.xlsx` files fails with an `openpyxl` error, install the project requirements:

```bash
pip install -r requirements.txt
```

### File not found

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

### No impedance blocks found

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

### Small samples are hard to see

Use the log-scale or zoomed Nyquist output:

```text
*_zpp_vs_zp_logscale.png
*_zpp_vs_zp_zoomed.png
```

Large impedance samples can make smaller samples appear compressed near the origin in the normal Nyquist plot.

### Raw markers are too large

Use a smaller marker size:

```bash
python auto_impedance_plots.py --fit-file data/fitted.xlsx --raw-file data/raw.xlsx --out plots --name "comparison" --marker-size 10
```

### Legend makes the image rectangular

This is expected. The graph panel itself is square, but the saved PNG may be rectangular so the legend can fit outside the plot area.
