"""
Automatic impedance plotter for sheets with repeated 5-column EIS blocks.

Expected block format:
Row 1: sample name in or near the first column of the block
Row 2: Freq, Z' (a), Z'' (b), Z, teta
Rows 3+: numeric data

This script creates five combined comparison plots. It supports either one
legacy input file or separate fitted and raw Excel files.
1. Nyquist plot: -Z'' vs Z'
2. Bode magnitude plot: log10(Z) vs log10(Freq)
3. Phase plot: -theta vs log10(Freq)

Usage:
    python auto_impedance_plots.py data.csv
    python auto_impedance_plots.py data.xlsx
    python auto_impedance_plots.py data.xlsx --sheet Sheet1 --out plots
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

# Use consistent publication-style typography for every generated figure.
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 16
plt.rcParams["axes.labelsize"] = 16
plt.rcParams["xtick.labelsize"] = 16
plt.rcParams["ytick.labelsize"] = 16
plt.rcParams["legend.fontsize"] = 12


HEADER_ROW = 1       # second row in Excel/CSV, zero-indexed here
DATA_START_ROW = 2   # third row in Excel/CSV, zero-indexed here


ColumnMap = Dict[str, int]


@dataclass
class BlockData:
    """Cleaned data and plotting row counts for one sample block."""

    sample_name: str
    data: pd.DataFrame
    plot_counts: Dict[str, int]
    source_type: str = "legacy"


MARKERS = ["o", "s", "^", "D", "v", "P", "X", "<", ">", "h", "*"]


def clean_name(value: object) -> str:
    """Convert a cell value into a safe, readable string."""
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def safe_filename_base(name: str) -> str:
    """Convert a user-provided plot name into a safe filename base."""
    text = clean_name(name).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "combined"


def normalize_header(value: object) -> str:
    """Normalize messy spreadsheet headers for matching."""
    text = clean_name(value).lower()
    text = text.replace("\u03a9", "ohm").replace("\u03c9", "ohm")
    text = text.replace("theta", "teta")
    text = text.replace("\u03b8", "teta")
    text = text.replace("\u2019", "'").replace("\u2032", "'")
    text = text.replace("\u2033", '"')
    text = text.replace("\u00b0", "")
    text = re.sub(r"ohms?", "", text)
    text = re.sub(r"degrees?", "", text)
    text = re.sub(r"deg", "", text)
    text = re.sub(r"[\s()\[\]{}|/\\,_-]+", "", text)
    return text


def is_frequency_header(header: str) -> bool:
    """Return True for frequency headers, including headers with units."""
    return header in {"f", "freq", "frequency"} or header.startswith(("freq", "frequency"))


def is_z_double_prime_header(header: str) -> bool:
    """Return True for the imaginary impedance column Z''."""
    return (
        header.startswith("z''")
        or header.startswith('z"')
        or "z''" in header
        or 'z"' in header
        or header in {"zdoubleprime", "zimag", "imagz", "zimaginary"}
    )


def is_z_prime_header(header: str) -> bool:
    """Return True for the real impedance column Z' without matching Z''."""
    if is_z_double_prime_header(header):
        return False

    return (
        header.startswith("z'")
        or header.startswith("zp")
        or header in {"zprime", "zreal", "realz", "zre", "rez"}
    )


def is_z_magnitude_header(header: str) -> bool:
    """Return True for the impedance magnitude column."""
    if is_z_prime_header(header) or is_z_double_prime_header(header):
        return False

    magnitude_headers = {
        "z",
        "zmod",
        "modz",
        "absz",
        "zabs",
        "mag",
        "magz",
        "zmag",
        "magnitude",
        "zmagnitude",
        "magnitudez",
        "modulus",
        "zmodulus",
        "modulusz",
        "impedance",
        "impedancemagnitude",
    }

    return header in magnitude_headers


def is_theta_header(header: str) -> bool:
    """Return True for phase/theta columns."""
    return "teta" in header or "phase" in header


def read_table(path: Path, sheet: Optional[str] = None) -> pd.DataFrame:
    """Read a CSV or Excel file without assuming a normal single header row."""
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, header=None)

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet or 0, header=None)

    raise ValueError("Input file must be .csv, .xlsx, or .xls")


def sample_name_for_block(raw: pd.DataFrame, start_col: int, block_number: int) -> str:
    """Get a readable sample name from row 1 of the block, or use a fallback."""
    search_end = min(start_col + 5, raw.shape[1])

    # Some sheets put the sample name above the first block column. Others use
    # a nearby cell in the same 5-column block, so check the whole block header.
    for col in range(start_col, search_end):
        sample_name = clean_name(raw.iat[0, col])
        if sample_name:
            return sample_name

    return f"Block {block_number}"


def header_match_name(header: str) -> str:
    """Return the impedance field name matched by a normalized header."""
    if is_frequency_header(header):
        return "freq"
    if is_z_double_prime_header(header):
        return "z_double_prime"
    if is_z_prime_header(header):
        return "z_prime"
    if is_z_magnitude_header(header):
        return "z"
    if is_theta_header(header):
        return "theta"
    return ""


def print_debug_block_headers(
    raw_headers: Dict[int, object],
    normalized_headers: Dict[int, str],
    column_map: ColumnMap,
) -> None:
    """Print raw and normalized headers for one possible block."""
    print("  Headers in this possible block:")
    for col in raw_headers:
        normalized = normalized_headers[col]
        matched_as = header_match_name(normalized) or "unmatched"
        mapped_as = ""
        for field_name, mapped_col in column_map.items():
            if mapped_col == col:
                mapped_as = f" -> {field_name}"
                break

        print(
            f"    column {col + 1}: raw={clean_name(raw_headers[col])!r}, "
            f"normalized={normalized!r}, detected={matched_as}{mapped_as}"
        )


def find_impedance_blocks(raw: pd.DataFrame, debug_headers: bool = False) -> List[Tuple[str, ColumnMap]]:
    """
    Find all repeated impedance data blocks.

    A block starts where the header row contains a frequency column. The next few
    columns are searched for Z', Z'', Z, and teta/theta.
    """
    blocks: List[Tuple[str, ColumnMap]] = []

    if raw.shape[0] <= DATA_START_ROW:
        raise ValueError("The file does not have enough rows to contain data.")

    header_values = [normalize_header(raw.iat[HEADER_ROW, col]) for col in range(raw.shape[1])]

    for start_col, header in enumerate(header_values):
        if not is_frequency_header(header):
            continue

        search_end = min(start_col + 5, raw.shape[1])
        raw_headers = {
            col: raw.iat[HEADER_ROW, col]
            for col in range(start_col, search_end)
        }
        block_headers = {
            col: normalize_header(raw.iat[HEADER_ROW, col])
            for col in range(start_col, search_end)
        }

        column_map: ColumnMap = {}

        for col, normalized in block_headers.items():
            matched_field = header_match_name(normalized)
            if matched_field and matched_field not in column_map:
                column_map[matched_field] = col

        required = {"freq", "z_prime", "z_double_prime", "z", "theta"}
        missing = required - set(column_map)
        if missing:
            print(
                f"Skipping possible block at column {start_col + 1}: "
                f"missing {', '.join(sorted(missing))}"
            )
            if debug_headers:
                print_debug_block_headers(raw_headers, block_headers, column_map)
            continue

        if debug_headers:
            print(f"Found block at column {start_col + 1}:")
            print_debug_block_headers(raw_headers, block_headers, column_map)

        sample_name = sample_name_for_block(raw, start_col, len(blocks) + 1)
        blocks.append((sample_name, column_map))

    return blocks


def build_clean_block(raw: pd.DataFrame, sample_name: str, column_map: ColumnMap) -> pd.DataFrame:
    """Extract one impedance block and compute all plotting columns."""
    data = pd.DataFrame(
        {
            "sample": sample_name,
            "freq": raw.iloc[DATA_START_ROW:, column_map["freq"]],
            "z_prime": raw.iloc[DATA_START_ROW:, column_map["z_prime"]],
            "z_double_prime": raw.iloc[DATA_START_ROW:, column_map["z_double_prime"]],
            "z": raw.iloc[DATA_START_ROW:, column_map["z"]],
            "theta": raw.iloc[DATA_START_ROW:, column_map["theta"]],
        }
    )

    numeric_columns = ["freq", "z_prime", "z_double_prime", "z", "theta"]
    for col in numeric_columns:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    # Avoid keeping completely empty trailing spreadsheet rows.
    data = data.dropna(subset=numeric_columns, how="all")

    # log10 is only valid for positive values. Non-positive values become NaN
    # and are skipped later only for plots that need the log columns.
    positive_freq = data["freq"].where(data["freq"] > 0)
    positive_z = data["z"].where(data["z"] > 0)

    data["log_freq"] = np.log10(positive_freq)
    data["log_z"] = np.log10(positive_z)
    data["neg_z_double_prime"] = -data["z_double_prime"]
    data["neg_theta"] = -data["theta"]

    return data


def count_plot_rows(data: pd.DataFrame) -> Dict[str, int]:
    """Count rows that have the required x/y values for each combined plot."""
    return {
        "zpp_vs_zp": len(data.dropna(subset=["z_prime", "neg_z_double_prime"])),
        "logz_vs_logf": len(data.dropna(subset=["log_freq", "log_z"])),
        "theta_vs_logf": len(data.dropna(subset=["log_freq", "neg_theta"])),
    }


def build_all_blocks(
    raw: pd.DataFrame,
    blocks: List[Tuple[str, ColumnMap]],
    source_type: str = "legacy",
) -> List[BlockData]:
    """Clean every detected block and keep only blocks with something to plot."""
    cleaned_blocks: List[BlockData] = []

    for sample_name, column_map in blocks:
        data = build_clean_block(raw, sample_name, column_map)
        plot_counts = count_plot_rows(data)

        if sum(plot_counts.values()) == 0:
            print(f"Skipping {sample_name}: no valid numeric rows found for any plot.")
            continue

        cleaned_blocks.append(BlockData(sample_name, data, plot_counts, source_type))

    return cleaned_blocks


def load_impedance_blocks(
    path: Path,
    sheet: Optional[str],
    source_type: str,
    debug_headers: bool = False,
) -> List[BlockData]:
    """Read, detect, and clean every impedance block in one source file."""
    raw_table = read_table(path, sheet=sheet)
    detected = find_impedance_blocks(raw_table, debug_headers=debug_headers)
    if not detected:
        raise ValueError(
            f"No impedance blocks found in {path}. Expected columns like: "
            "Freq, Z', Z'', Z, teta."
        )
    return build_all_blocks(raw_table, detected, source_type)


def collect_sample_names(blocks: List[BlockData]) -> List[str]:
    """Return unique sample names in their first-seen order."""
    return list(dict.fromkeys(block.sample_name for block in blocks))


def sample_identity(sample_name: str) -> str:
    """Normalize harmless label differences when matching fit and raw samples."""
    identity = re.sub(r"[^a-z0-9]+", "", sample_name.lower())
    return identity or sample_name.lower()


def make_color_map(sample_names: List[str]) -> Dict[str, object]:
    """Assign one color to each sample, shared by fit and raw data."""
    colors = plt.get_cmap("tab20").colors
    identities = list(dict.fromkeys(sample_identity(name) for name in sample_names))
    identity_colors = {
        identity: colors[index % len(colors)]
        for index, identity in enumerate(identities)
    }
    return {name: identity_colors[sample_identity(name)] for name in sample_names}


def make_marker_map(sample_names: List[str]) -> Dict[str, str]:
    """Assign a repeatable hollow-marker shape to each sample."""
    identities = list(dict.fromkeys(sample_identity(name) for name in sample_names))
    identity_markers = {
        identity: MARKERS[index % len(MARKERS)]
        for index, identity in enumerate(identities)
    }
    return {name: identity_markers[sample_identity(name)] for name in sample_names}


def legend_options(sample_count: int) -> Dict[str, object]:
    """Choose a readable legend layout for small or large sample counts."""
    if sample_count > 8:
        return {
            "bbox_to_anchor": (1.02, 1),
            "loc": "upper left",
            "borderaxespad": 0,
            "fontsize": 12,
            "frameon": True,
        }

    return {"loc": "best", "fontsize": 12}


def style_axis(ax: plt.Axes) -> None:
    """Apply shared journal-style borders and ticks to one set of axes."""
    ax.grid(False)
    # Keep the graph panel square even when an outside legend uses extra room.
    ax.set_box_aspect(1)
    ax.tick_params(direction="in", top=True, right=True)

    # A slightly heavier box keeps the plotting area crisp when printed.
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1.2)


def choose_scientific_scale(values: object) -> int:
    """Choose a power of ten that makes large tick values easy to read.

    For example, data reaching 8,000,000,000 returns 9, so the displayed
    values can be divided by 10^9. Values below 1,000 need no scaling and
    return zero.
    """
    numeric_values = np.asarray(values, dtype=float)
    finite_values = numeric_values[np.isfinite(numeric_values)]
    if finite_values.size == 0:
        return 0

    largest_value = np.max(np.abs(finite_values))
    if largest_value == 0:
        return 0

    exponent = int(np.floor(np.log10(largest_value)))
    return exponent if exponent >= 3 else 0


def format_scaled_axis_label(
    base_label: str,
    unit: Optional[str],
    exponent: int,
) -> str:
    r"""Return a mathtext label with scaling before the slash and unit.

    For example, an exponent of 9 produces
    ``Z' × 10^9 / Ω``. With an exponent of zero, it produces ``Z' / Ω``.
    The unit should use mathtext notation, such as ``r"\Omega"``.
    """
    quantity = base_label
    if exponent:
        quantity = rf"{quantity} \times 10^{{{exponent}}}"

    if unit:
        quantity = rf"{quantity} \,/\, {unit}"

    return rf"${quantity}$"


def apply_scaled_axis(
    ax: plt.Axes,
    axis: str,
    values: object,
    base_label: str,
    unit: Optional[str] = None,
) -> int:
    """Scale linear-axis ticks and put the power of ten in the axis label."""
    exponent = choose_scientific_scale(values)
    axis_object = ax.xaxis if axis == "x" else ax.yaxis

    if exponent:
        scale = 10.0 ** exponent

        def format_scaled_tick(value: float, _position: int) -> str:
            scaled_value = value / scale
            # Avoid displaying a distracting negative zero near the origin.
            if abs(scaled_value) < 1e-12:
                scaled_value = 0.0
            return f"{scaled_value:g}"

        axis_object.set_major_formatter(FuncFormatter(format_scaled_tick))
    else:
        # Plain formatting also suppresses Matplotlib's corner offset text.
        axis_object.set_major_formatter(FuncFormatter(lambda value, _position: f"{value:g}"))

    label = format_scaled_axis_label(base_label, unit, exponent)
    axis_object.set_label_text(label)
    axis_object.offsetText.set_visible(False)
    return exponent


def collect_axis_values(blocks: List[BlockData], column: str) -> np.ndarray:
    """Collect valid values from one plotting column across all samples."""
    series = [block.data[column].dropna() for block in blocks]
    if not series:
        return np.array([], dtype=float)
    return pd.concat(series, ignore_index=True).to_numpy(dtype=float)


def draw_blocks_on_axes(
    ax: plt.Axes,
    blocks: List[BlockData],
    x_col: str,
    y_col: str,
    positive_only: bool = False,
    color_map: Optional[Dict[str, object]] = None,
    marker_map: Optional[Dict[str, str]] = None,
    marker_size: float = 20,
    line_width: float = 1.5,
) -> None:
    """Draw fits as lines, raw data as hollow markers, and legacy as before."""
    color_map = color_map or make_color_map(collect_sample_names(blocks))
    marker_map = marker_map or make_marker_map(collect_sample_names(blocks))
    for block in blocks:
        plot_data = block.data.dropna(subset=[x_col, y_col])

        # Log-scaled plots can only display positive x and y values.
        if positive_only:
            plot_data = plot_data[(plot_data[x_col] > 0) & (plot_data[y_col] > 0)]

        if plot_data.empty:
            continue

        color = color_map[block.sample_name]
        if block.source_type == "fit":
            ax.plot(
                plot_data[x_col], plot_data[y_col], linestyle="-", linewidth=line_width,
                color=color, label=f"{block.sample_name} fit",
            )
        elif block.source_type == "raw":
            ax.scatter(
                plot_data[x_col], plot_data[y_col], marker=marker_map[block.sample_name],
                facecolors="none", edgecolors=color, linewidths=1.2, s=marker_size,
                label=f"{block.sample_name} raw",
            )
        else:
            # Preserve the original one-file filled-scatter behavior.
            ax.scatter(
                plot_data[x_col], plot_data[y_col], s=22, color=color,
                label=block.sample_name,
            )


def finish_and_save_plot(
    fig: plt.Figure,
    ax: plt.Axes,
    output_path: Path,
) -> None:
    """Apply common plot formatting and save at high resolution."""
    style_axis(ax)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(**legend_options(len(labels)))

    fig.tight_layout()
    # Tight cropping retains the labels and outside legend on the wider canvas.
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_combined_scatter_plot(
    blocks: List[BlockData],
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
    output_path: Path,
    scientific_axis_labels: bool = False,
    color_map: Optional[Dict[str, object]] = None,
    marker_map: Optional[Dict[str, str]] = None,
    marker_size: float = 20,
    line_width: float = 1.5,
) -> None:
    """Save one combined scatter plot with every sample on the same axes."""
    # The extra width leaves room for a legend beside the square graph panel.
    fig, ax = plt.subplots(figsize=(8.5, 6))

    draw_blocks_on_axes(
        ax, blocks, x_col, y_col, color_map=color_map, marker_map=marker_map,
        marker_size=marker_size, line_width=line_width,
    )
    if scientific_axis_labels:
        apply_scaled_axis(ax, "x", collect_axis_values(blocks, x_col), "Z'", r"\Omega")
        apply_scaled_axis(ax, "y", collect_axis_values(blocks, y_col), "-Z''", r"\Omega")
    else:
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

    finish_and_save_plot(fig, ax, output_path)


def get_zoom_limits(blocks: List[BlockData], percentile: float) -> Tuple[Optional[float], Optional[float]]:
    """Return percentile-based axis limits for the zoomed Nyquist plot."""
    all_x_values: List[pd.Series] = []
    all_y_values: List[pd.Series] = []

    for block in blocks:
        plot_data = block.data.dropna(subset=["z_prime", "neg_z_double_prime"])
        if plot_data.empty:
            continue

        all_x_values.append(plot_data["z_prime"])
        all_y_values.append(plot_data["neg_z_double_prime"])

    if not all_x_values or not all_y_values:
        return None, None

    x_limit = np.nanpercentile(pd.concat(all_x_values), percentile)
    y_limit = np.nanpercentile(pd.concat(all_y_values), percentile)

    # Bad or non-positive limits should not crash plotting. In that case, the
    # zoomed plot is still saved, just without manually forced axis limits.
    if not np.isfinite(x_limit) or x_limit <= 0:
        x_limit = None
    if not np.isfinite(y_limit) or y_limit <= 0:
        y_limit = None

    return x_limit, y_limit


def save_nyquist_logscale_plot(
    blocks: List[BlockData],
    output_path: Path,
    color_map: Dict[str, object],
    marker_map: Dict[str, str],
    marker_size: float = 20,
    line_width: float = 1.5,
) -> None:
    """Save a log-log Nyquist plot, using only positive x and y values."""
    fig, ax = plt.subplots(figsize=(8.5, 6))

    draw_blocks_on_axes(
        ax, blocks, "z_prime", "neg_z_double_prime", positive_only=True,
        color_map=color_map, marker_map=marker_map,
        marker_size=marker_size, line_width=line_width,
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Z' / Ω")
    ax.set_ylabel("-Z'' / Ω")
    # Logarithmic tick formatting is clearest when left to Matplotlib.
    ax.xaxis.offsetText.set_visible(False)
    ax.yaxis.offsetText.set_visible(False)
    finish_and_save_plot(fig, ax, output_path)


def save_nyquist_zoomed_plot(
    blocks: List[BlockData],
    output_path: Path,
    zoom_percentile: float,
    scientific_axis_labels: bool,
    color_map: Dict[str, object],
    marker_map: Dict[str, str],
    marker_size: float = 20,
    line_width: float = 1.5,
) -> None:
    """Save a Nyquist plot zoomed to ignore the largest outliers."""
    fig, ax = plt.subplots(figsize=(8.5, 6))

    draw_blocks_on_axes(
        ax, blocks, "z_prime", "neg_z_double_prime",
        color_map=color_map, marker_map=marker_map,
        marker_size=marker_size, line_width=line_width,
    )

    x_limit, y_limit = get_zoom_limits(blocks, zoom_percentile)
    if x_limit is not None:
        ax.set_xlim(left=0, right=x_limit)
    if y_limit is not None:
        ax.set_ylim(bottom=0, top=y_limit)

    if scientific_axis_labels:
        x_values = collect_axis_values(blocks, "z_prime")
        y_values = collect_axis_values(blocks, "neg_z_double_prime")
        if x_limit is not None:
            x_values = x_values[(x_values >= 0) & (x_values <= x_limit)]
        if y_limit is not None:
            y_values = y_values[(y_values >= 0) & (y_values <= y_limit)]
        apply_scaled_axis(ax, "x", x_values, "Z'", r"\Omega")
        apply_scaled_axis(ax, "y", y_values, "-Z''", r"\Omega")
    else:
        ax.set_xlabel("Z' / Ω")
        ax.set_ylabel("-Z'' / Ω")

    finish_and_save_plot(fig, ax, output_path)


def plot_combined_blocks(
    blocks: List[BlockData],
    out_dir: Path,
    plot_name: Optional[str] = None,
    zoom_percentile: float = 90,
    scientific_axis_labels: bool = True,
    marker_size: float = 20,
    line_width: float = 1.5,
) -> List[Path]:
    """Create the combined scatter plots."""
    filename_base = safe_filename_base(plot_name) if plot_name else "combined"
    sample_names = collect_sample_names(blocks)
    color_map = make_color_map(sample_names)
    marker_map = make_marker_map(sample_names)

    saved_paths: List[Path] = []

    normal_nyquist_path = out_dir / f"{filename_base}_zpp_vs_zp.png"
    save_combined_scatter_plot(
        blocks,
        "z_prime",
        "neg_z_double_prime",
        "Z' / Ω",
        "-Z'' / Ω",
        normal_nyquist_path,
        scientific_axis_labels=scientific_axis_labels,
        color_map=color_map,
        marker_map=marker_map,
        marker_size=marker_size,
        line_width=line_width,
    )
    saved_paths.append(normal_nyquist_path)

    logscale_nyquist_path = out_dir / f"{filename_base}_zpp_vs_zp_logscale.png"
    save_nyquist_logscale_plot(
        blocks,
        logscale_nyquist_path,
        color_map,
        marker_map,
        marker_size,
        line_width,
    )
    saved_paths.append(logscale_nyquist_path)

    zoomed_nyquist_path = out_dir / f"{filename_base}_zpp_vs_zp_zoomed.png"
    save_nyquist_zoomed_plot(
        blocks,
        zoomed_nyquist_path,
        zoom_percentile,
        scientific_axis_labels,
        color_map,
        marker_map,
        marker_size,
        line_width,
    )
    saved_paths.append(zoomed_nyquist_path)

    plots = [
        (
            f"{filename_base}_logz_vs_logf.png",
            "log_freq",
            "log_z",
            "log f",
            "log |Z|",
        ),
        (
            f"{filename_base}_theta_vs_logf.png",
            "log_freq",
            "neg_theta",
            "log f",
            "-θ / degrees",
        ),
    ]

    for filename, x_col, y_col, x_label, y_label in plots:
        output_path = out_dir / filename
        save_combined_scatter_plot(
            blocks, x_col, y_col, x_label, y_label, output_path,
            color_map=color_map, marker_map=marker_map,
            marker_size=marker_size, line_width=line_width,
        )
        saved_paths.append(output_path)

    return saved_paths


def save_cleaned_csv(blocks: List[BlockData], out_dir: Path) -> Path:
    """Save one combined cleaned CSV with sample and source columns."""
    cleaned_path = out_dir / "combined_cleaned_impedance_data.csv"
    frames = []
    for block in blocks:
        frame = block.data.copy()
        frame.insert(1, "source_type", block.source_type)
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(cleaned_path, index=False)
    return cleaned_path


def print_summary(
    blocks: List[BlockData],
    saved_plots: List[Path],
    cleaned_path: Optional[Path],
    fit_path: Optional[Path] = None,
    raw_path: Optional[Path] = None,
) -> None:
    """Print a short terminal summary for the user."""
    if fit_path is not None:
        print(f"\nFitted file: {fit_path}")
    if raw_path is not None:
        print(f"Raw file: {raw_path}")

    if fit_path is not None or raw_path is not None:
        print(f"Fitted blocks found: {sum(b.source_type == 'fit' for b in blocks)}")
        print(f"Raw blocks found: {sum(b.source_type == 'raw' for b in blocks)}")
    else:
        print(f"\nValid blocks found: {len(blocks)}")

    for block in blocks:
        counts = block.plot_counts
        print(
            f"- {block.sample_name}"
            f"{' ' + block.source_type if block.source_type != 'legacy' else ''}: "
            f"{counts['zpp_vs_zp']} rows for -Z'' vs Z', "
            f"{counts['logz_vs_logf']} rows for log Z vs log F, "
            f"{counts['theta_vs_logf']} rows for -theta vs log F"
        )

    print("\nSaved combined plots:")
    for path in saved_plots:
        print(f"- {path}")

    if cleaned_path is not None:
        print(f"\nSaved cleaned CSV: {cleaned_path}")

    print("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatically plot impedance scatter plots from repeated 5-column CSV/Excel blocks."
    )
    parser.add_argument(
        "input_file", nargs="?", help="Legacy path to one .csv, .xlsx, or .xls file"
    )
    parser.add_argument("--fit-file", help="Path to a fitted-data .xlsx file")
    parser.add_argument("--raw-file", help="Path to a raw/unfitted-data .xlsx file")
    parser.add_argument("--sheet", default=None, help="Excel sheet name. Not needed for CSV files.")
    parser.add_argument("--out", default="plots", help="Output folder for generated PNG plots")
    parser.add_argument(
        "--cleaned-csv",
        action="store_true",
        help="Also save one combined cleaned CSV file with a sample column.",
    )
    parser.add_argument(
        "--debug-headers",
        action="store_true",
        help="Print raw and normalized headers for each possible impedance block.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional base name used in output filenames, for example: '10 days'.",
    )
    parser.add_argument(
        "--zoom-percentile",
        type=float,
        default=90,
        help="Percentile used for zoomed Nyquist axis limits. Default: 90.",
    )
    parser.add_argument(
        "--marker-size",
        type=float,
        default=20,
        help="Size of raw/unfitted hollow markers. Default: 20.",
    )
    parser.add_argument(
        "--line-width",
        type=float,
        default=1.5,
        help="Width of fitted-data lines. Default: 1.5.",
    )
    scientific_group = parser.add_mutually_exclusive_group()
    scientific_group.add_argument(
        "--scientific-axis-labels",
        dest="scientific_axis_labels",
        action="store_true",
        help="Put automatic powers of ten in linear Nyquist axis labels (default).",
    )
    scientific_group.add_argument(
        "--no-scientific-axis-labels",
        dest="scientific_axis_labels",
        action="store_false",
        help="Use Matplotlib's standard linear Nyquist axis formatting.",
    )
    parser.set_defaults(scientific_axis_labels=True)

    args = parser.parse_args()

    if not any((args.input_file, args.fit_file, args.raw_file)):
        parser.error("provide input_file, --fit-file, or --raw-file")
    if args.marker_size <= 0:
        parser.error("--marker-size must be greater than 0")
    if args.line_width <= 0:
        parser.error("--line-width must be greater than 0")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    fit_path = Path(args.fit_file) if args.fit_file else None
    raw_path = Path(args.raw_file) if args.raw_file else None

    # Explicit fit/raw options select comparison mode. A positional file is
    # retained for backward compatibility and is used only in legacy mode.
    if fit_path is not None or raw_path is not None:
        cleaned_blocks: List[BlockData] = []
        if fit_path is not None:
            cleaned_blocks.extend(load_impedance_blocks(
                fit_path, args.sheet, "fit", args.debug_headers
            ))
        if raw_path is not None:
            cleaned_blocks.extend(load_impedance_blocks(
                raw_path, args.sheet, "raw", args.debug_headers
            ))
    else:
        input_path = Path(args.input_file)
        cleaned_blocks = load_impedance_blocks(
            input_path, args.sheet, "legacy", args.debug_headers
        )

    if not cleaned_blocks:
        raise ValueError("No valid numeric impedance data found in the detected blocks.")

    if not 0 < args.zoom_percentile <= 100:
        raise ValueError("--zoom-percentile must be greater than 0 and less than or equal to 100.")

    saved_plots = plot_combined_blocks(
        cleaned_blocks,
        out_dir,
        plot_name=args.name,
        zoom_percentile=args.zoom_percentile,
        scientific_axis_labels=args.scientific_axis_labels,
        marker_size=args.marker_size,
        line_width=args.line_width,
    )

    cleaned_path = None
    if args.cleaned_csv:
        cleaned_path = save_cleaned_csv(cleaned_blocks, out_dir)

    print_summary(cleaned_blocks, saved_plots, cleaned_path, fit_path, raw_path)


if __name__ == "__main__":
    main()
