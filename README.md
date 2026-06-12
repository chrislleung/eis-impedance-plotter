# CSV Plotter

This project contains Python tools for plotting spreadsheet data.

The main script is `auto_impedance_plots.py`, which reads impedance data from
Excel or CSV files, detects repeated 5-column impedance blocks, and creates
combined comparison plots for all samples.

There is also an older interactive helper script, `plot_csv.py`, for making a
simple plot from selected CSV columns.

## Features

`auto_impedance_plots.py` can:

* Read `.xlsx`, `.xls`, and `.csv` files
* Detect repeated 5-column impedance blocks automatically
* Use sample names from the sheet as legend labels
* Create combined comparison plots with each sample in a different color
* Save plots to an output folder
* Use a custom base name for plot titles and output filenames
* Export cleaned computed data with `--cleaned-csv`
* Print debug information for header matching with `--debug-headers`

## Expected Data Format

The impedance script expects repeated blocks across the sheet. Each block is
usually 5 columns wide:

```text
Freq    Z' (a)    Z'' (b)    Z or Mag    teta or Phase
```

The first row of each block can contain the sample name. The second row should
contain the headers. Data starts on the third row.

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

## Installation

Create and activate a virtual environment if you want one:

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## Basic Usage

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

Use `--name` to customize plot titles and output filenames:

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

The plot titles will start with the provided name, for example:

```text
10 days -Z'' vs Z'
10 days -Z'' vs Z' log scale
10 days -Z'' vs Z' zoomed
10 days log Z vs log F
10 days -theta vs log F
```

## Output Plots

The script creates five PNG files:

* Normal Nyquist plot: `-Z'' vs Z'`
* Log-scale Nyquist plot: `-Z'' vs Z'` with log x/y axes
* Zoomed Nyquist plot: `-Z'' vs Z'` with extreme outliers ignored for axis limits
* Bode magnitude plot: `log Z vs log F`
* Phase plot: `-theta vs log F`

The log-scale Nyquist plot only includes rows where both `Z'` and `-Z''` are
positive.

## Zoom Control

The zoomed Nyquist plot uses percentile-based axis limits. The default is `90`,
which means the largest 10 percent of values are ignored when setting the
zoomed axis range.

Change it with:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --zoom-percentile 85
```

## Excel Sheet Selection

For Excel files, the first sheet is used by default. To choose a sheet:

```bash
python auto_impedance_plots.py data/10days.xlsx --sheet Sheet1 --out plots
```

## Cleaned CSV Export

Use `--cleaned-csv` to save the cleaned computed data:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --cleaned-csv
```

This creates:

```text
plots/combined_cleaned_impedance_data.csv
```

The cleaned CSV includes a `sample` column and computed columns such as
`log_freq`, `log_z`, `neg_z_double_prime`, and `neg_theta`.

## Debug Header Detection

If blocks are skipped because a header is not recognized, run with:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --debug-headers
```

This prints each possible block's raw headers, normalized headers, and detected
column type. It is useful when a spreadsheet uses unusual column names.

## Common Commands

Basic run:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots
```

Run with custom title/name:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days"
```

Run with a different zoom percentile:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --zoom-percentile 85
```

Run with cleaned CSV export:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --name "10 days" --cleaned-csv
```

## Generic CSV Plotter

The project also includes `plot_csv.py`, an interactive script for simple CSV
plots.

Run it with:

```bash
python plot_csv.py
```

It asks for the CSV file path, x-axis column, y-axis column, graph type, and
whether to save the result as an image.

## Troubleshooting

### Missing Excel dependency

If reading `.xlsx` files fails with an `openpyxl` error, install the project
requirements:

```bash
pip install -r requirements.txt
```

### No impedance blocks found

Use `--debug-headers` to see how the script is reading the headers:

```bash
python auto_impedance_plots.py data/10days.xlsx --out plots --debug-headers
```

Check that each block has headers for frequency, `Z'`, `Z''`, magnitude `Z`,
and theta/phase.

### Small samples are hard to see

Use the log-scale or zoomed Nyquist output:

```text
*_zpp_vs_zp_logscale.png
*_zpp_vs_zp_zoomed.png
```
