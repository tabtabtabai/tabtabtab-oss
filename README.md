# TabTabTab Extensions

This package contains extensions for TabTabTab.

## Prerequisites

Before you begin development, ensure you have Poetry installed for dependency management:


### Install poetry
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Install dependencies
```bash
poetry install
```

### Activate virtual environment
```bash
poetry shell
```
or in an IDE like VS Code or Cursor, you can activate the virtual environment by cmd+shift+p and then typing "Python: Select Interpreter" and selecting the one created by poetry.


## Adding a New Extension

To add a new extension to this repository, follow these steps:

### Define an ID
1. Add a unique identifier for your extension to the `EXTENSION_ID` enum in `extension_constants.py`.
2. Define the list of dependencies required for your extension in the `EXTENSION_DEPENDENCIES` enum in `extension_constants.py`. Users will be able
to manage these dependencies via the TabTabTab app (Menu -> Manage Extensions).

### Register the Extension
Add an `ExtensionDescriptor` instance for your extension to the `EXTENSION_DIRECTORY` list in `extension_directory.py`. This descriptor links the ID, description, dependencies, and the extension class itself.

### Implement the Extension
Create a new directory for your extension under `extensions/` (e.g., `extensions/my_new_extension/`) and place your extension's Python code there. Your main extension class should inherit from `ExtensionInterface` (from `tabtabtab-lib`).

### Reference Existing Examples
Look at the code in `extensions/sample_extension/` or other existing extensions for examples of how to structure your code and implement the required methods (`on_copy`, `on_paste`, `on_context_request`).

### Update requirements.txt
Update the `requirements.txt` file to include the new dependencies.
```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
```

### Make a Pull Request
Once your change is merged to the main branch, it will be live and ready to use in the TabTabTab app!


## Testing Locally

You can test your extension locally using the provided local runner script.

### The Runner
The script `local_runner/main.py` is designed to instantiate and run a single extension.

### Configuration
You need to modify `local_runner/main.py` to:
    *   Import your extension class.
    *   Pass your extension class to the `main()` function call at the bottom of the script.
    *   Ensure the `dependencies` dictionary within the `if __name__ == "__main__":` block includes the necessary keys (from `EXTENSION_DEPENDENCIES`) and retrieves their values (e.g., from environment variables loaded via a `.env` file).

### Running
You can run the script from your terminal:
    ```bash
    python local_runner/main.py <action>
    ```
    Where `<action>` is `copy`, `paste`, `context`, or `all`.

### Debugging
For debugging within VS Code or Cursor, you can use the provided `local_runner/sample_launch.json` as a template. Copy its contents into your `.vscode/launch.json` and adjust the `"program"` path and any environment variables (`"env"`) as needed for your specific extension. This allows you to set breakpoints and step through your extension's code. Make sure the `PYTHONPATH` in the launch configuration points to the project root so imports work correctly.
