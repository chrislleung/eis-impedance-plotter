"""
Automatic impedance plotter for sheets with repeated 5-column EIS blocks.

Expected block format:
Row 1: sample name in or near the first column of the block
Row 2: Freq, Z' (a), Z'' (b), Z, teta
Rows 3+: numeric data

This script creates three combined comparison plots:
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


HEADER_ROW = 1       # second row in Excel/CSV, zero-indexed here
DATA_START_ROW = 2   # third row in Excel/CSV, zero-indexed here


ColumnMap = Dict[str, int]


@dataclass
class BlockData:
    """Cleaned data and plotting row counts for one sample block."""

    sample_name: str
    data: pd.DataFrame
    plot_counts: Dict[str, int]


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


def build_all_blocks(raw: pd.DataFrame, blocks: List[Tuple[str, ColumnMap]]) -> List[BlockData]:
    """Clean every detected block and keep only blocks with something to plot."""
    cleaned_blocks: List[BlockData] = []

    for sample_name, column_map in blocks:
        data = build_clean_block(raw, sample_name, column_map)
        plot_counts = count_plot_rows(data)

        if sum(plot_counts.values()) == 0:
            print(f"Skipping {sample_name}: no valid numeric rows found for any plot.")
            continue

        cleaned_blocks.append(BlockData(sample_name, data, plot_counts))

    return cleaned_blocks


def legend_options(sample_count: int) -> Dict[str, object]:
    """Choose a readable legend layout for small or large sample counts."""
    if sample_count > 8:
        return {
            "bbox_to_anchor": (1.02, 1),
            "loc": "upper left",
            "borderaxespad": 0,
            "fontsize": "small",
        }

    return {"loc": "best", "fontsize": "small"}


def draw_blocks_on_axes(
    ax: plt.Axes,
    blocks: List[BlockData],
    x_col: str,
    y_col: str,
    positive_only: bool = False,
) -> None:
    """Draw every sample block on one set of axes."""
    for block in blocks:
        plot_data = block.data.dropna(subset=[x_col, y_col])

        # Log-scaled plots can only display positive x and y values.
        if positive_only:
            plot_data = plot_data[(plot_data[x_col] > 0) & (plot_data[y_col] > 0)]

        if plot_data.empty:
            continue

        ax.scatter(plot_data[x_col], plot_data[y_col], s=22, label=block.sample_name)


def finish_and_save_plot(
    fig: plt.Figure,
    ax: plt.Axes,
    x_label: str,
    y_label: str,
    title: str,
    output_path: Path,
) -> None:
    """Apply common plot formatting and save at high resolution."""
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(**legend_options(len(labels)))

    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def save_combined_scatter_plot(
    blocks: List[BlockData],
    x_col: str,
    y_col: str,
    x_label: str,
    y_label: str,
    title: str,
    output_path: Path,
) -> None:
    """Save one combined scatter plot with every sample on the same axes."""
    fig_width = 8 if len(blocks) <= 8 else 10
    fig, ax = plt.subplots(figsize=(fig_width, 5.5))

    draw_blocks_on_axes(ax, blocks, x_col, y_col)
    finish_and_save_plot(fig, ax, x_label, y_label, title, output_path)


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
    title: str,
    output_path: Path,
) -> None:
    """Save a log-log Nyquist plot, using only positive x and y values."""
    fig_width = 8 if len(blocks) <= 8 else 10
    fig, ax = plt.subplots(figsize=(fig_width, 5.5))

    draw_blocks_on_axes(ax, blocks, "z_prime", "neg_z_double_prime", positive_only=True)
    ax.set_xscale("log")
    ax.set_yscale("log")
    finish_and_save_plot(fig, ax, "Z'", "-Z''", title, output_path)


def save_nyquist_zoomed_plot(
    blocks: List[BlockData],
    title: str,
    output_path: Path,
    zoom_percentile: float,
) -> None:
    """Save a Nyquist plot zoomed to ignore the largest outliers."""
    fig_width = 8 if len(blocks) <= 8 else 10
    fig, ax = plt.subplots(figsize=(fig_width, 5.5))

    draw_blocks_on_axes(ax, blocks, "z_prime", "neg_z_double_prime")

    x_limit, y_limit = get_zoom_limits(blocks, zoom_percentile)
    if x_limit is not None:
        ax.set_xlim(left=0, right=x_limit)
    if y_limit is not None:
        ax.set_ylim(bottom=0, top=y_limit)

    finish_and_save_plot(fig, ax, "Z'", "-Z''", title, output_path)


def plot_combined_blocks(
    blocks: List[BlockData],
    out_dir: Path,
    plot_name: Optional[str] = None,
    zoom_percentile: float = 90,
) -> List[Path]:
    """Create the combined scatter plots."""
    filename_base = safe_filename_base(plot_name) if plot_name else "combined"
    title_base = clean_name(plot_name) if plot_name else "Combined"

    saved_paths: List[Path] = []

    normal_nyquist_path = out_dir / f"{filename_base}_zpp_vs_zp.png"
    save_combined_scatter_plot(
        blocks,
        "z_prime",
        "neg_z_double_prime",
        "Z'",
        "-Z''",
        f"{title_base} -Z'' vs Z'",
        normal_nyquist_path,
    )
    saved_paths.append(normal_nyquist_path)

    logscale_nyquist_path = out_dir / f"{filename_base}_zpp_vs_zp_logscale.png"
    save_nyquist_logscale_plot(
        blocks,
        f"{title_base} -Z'' vs Z' log scale",
        logscale_nyquist_path,
    )
    saved_paths.append(logscale_nyquist_path)

    zoomed_nyquist_path = out_dir / f"{filename_base}_zpp_vs_zp_zoomed.png"
    save_nyquist_zoomed_plot(
        blocks,
        f"{title_base} -Z'' vs Z' zoomed",
        zoomed_nyquist_path,
        zoom_percentile,
    )
    saved_paths.append(zoomed_nyquist_path)

    plots = [
        (
            f"{filename_base}_logz_vs_logf.png",
            "log_freq",
            "log_z",
            "log F",
            "log Z",
            f"{title_base} log Z vs log F",
        ),
        (
            f"{filename_base}_theta_vs_logf.png",
            "log_freq",
            "neg_theta",
            "log F",
            "-theta",
            f"{title_base} -theta vs log F",
        ),
    ]

    for filename, x_col, y_col, x_label, y_label, title in plots:
        output_path = out_dir / filename
        save_combined_scatter_plot(blocks, x_col, y_col, x_label, y_label, title, output_path)
        saved_paths.append(output_path)

    return saved_paths


def save_cleaned_csv(blocks: List[BlockData], out_dir: Path) -> Path:
    """Save one combined cleaned CSV with a sample column."""
    cleaned_path = out_dir / "combined_cleaned_impedance_data.csv"
    combined = pd.concat([block.data for block in blocks], ignore_index=True)
    combined.to_csv(cleaned_path, index=False)
    return cleaned_path


def print_summary(blocks: List[BlockData], saved_plots: List[Path], cleaned_path: Optional[Path]) -> None:
    """Print a short terminal summary for the user."""
    print(f"\nValid blocks found: {len(blocks)}")

    for block in blocks:
        counts = block.plot_counts
        print(
            f"- {block.sample_name}: "
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
    parser.add_argument("input_file", help="Path to the .csv, .xlsx, or .xls file")
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
        help="Optional base name used in plot titles and output filenames, for example: '10 days'.",
    )
    parser.add_argument(
        "--zoom-percentile",
        type=float,
        default=90,
        help="Percentile used for zoomed Nyquist axis limits. Default: 90.",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = read_table(input_path, sheet=args.sheet)
    blocks = find_impedance_blocks(raw, debug_headers=args.debug_headers)

    if not blocks:
        raise ValueError(
            "No impedance blocks found. Expected a header row containing columns like: "
            "Freq, Z' (a), Z'' (b), Z, teta."
        )

    cleaned_blocks = build_all_blocks(raw, blocks)

    if not cleaned_blocks:
        raise ValueError("No valid numeric impedance data found in the detected blocks.")

    if not 0 < args.zoom_percentile <= 100:
        raise ValueError("--zoom-percentile must be greater than 0 and less than or equal to 100.")

    saved_plots = plot_combined_blocks(
        cleaned_blocks,
        out_dir,
        plot_name=args.name,
        zoom_percentile=args.zoom_percentile,
    )

    cleaned_path = None
    if args.cleaned_csv:
        cleaned_path = save_cleaned_csv(cleaned_blocks, out_dir)

    print_summary(cleaned_blocks, saved_plots, cleaned_path)


if __name__ == "__main__":
    main()
