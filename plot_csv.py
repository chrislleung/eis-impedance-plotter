import pandas as pd
import matplotlib.pyplot as plt


def load_csv(file_path):
    """Load a CSV file and return it as a pandas DataFrame."""
    try:
        data = pd.read_csv(file_path)
        return data
    except FileNotFoundError:
        print("Error: File not found. Check the file path and try again.")
        return None
    except Exception as error:
        print(f"Error loading CSV file: {error}")
        return None


def show_columns(data):
    """Print all available columns in the CSV file."""
    print("\nAvailable columns:")
    for column in data.columns:
        print(f"- {column}")


def choose_column(data, axis_name):
    """Ask the user to choose a valid column."""
    while True:
        column = input(f"\nEnter the column for the {axis_name}-axis: ")

        if column in data.columns:
            return column

        print(f"'{column}' is not a valid column.")
        print("Please choose one of these columns:")
        for available_column in data.columns:
            print(f"- {available_column}")


def choose_graph_type():
    """Ask the user to choose a graph type."""
    valid_graphs = ["line", "scatter", "bar"]

    while True:
        graph_type = input("\nChoose graph type: line, scatter, or bar: ").lower()

        if graph_type in valid_graphs:
            return graph_type

        print("Invalid graph type. Please type line, scatter, or bar.")


def plot_graph(data, x_column, y_column, graph_type):
    """Plot the selected graph."""
    plt.figure(figsize=(10, 6))

    if graph_type == "line":
        plt.plot(data[x_column], data[y_column], marker="o")
    elif graph_type == "scatter":
        plt.scatter(data[x_column], data[y_column])
    elif graph_type == "bar":
        plt.bar(data[x_column], data[y_column])

    plt.xlabel(x_column)
    plt.ylabel(y_column)
    plt.title(f"{y_column} vs {x_column}")
    plt.xticks(rotation=45)
    plt.tight_layout()

    save_choice = input("\nDo you want to save the graph as an image? yes/no: ").lower()

    if save_choice == "yes":
        output_name = input("Enter output filename, for example graph.png: ")

        if not output_name.endswith(".png"):
            output_name += ".png"

        plt.savefig(output_name, dpi=300)
        print(f"Graph saved as {output_name}")

    plt.show()


def main():
    print("CSV Graph Plotter")

    file_path = input("\nEnter the path to your CSV file: ")

    data = load_csv(file_path)

    if data is None:
        return

    print("\nCSV loaded successfully.")
    print("\nFirst few rows of your data:")
    print(data.head())

    show_columns(data)

    x_column = choose_column(data, "x")
    y_column = choose_column(data, "y")
    graph_type = choose_graph_type()

    plot_graph(data, x_column, y_column, graph_type)


if __name__ == "__main__":
    main()