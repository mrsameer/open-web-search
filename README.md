# Open Web Search

A free, open-source web search engine built with Python, FastAPI, and DuckDuckGo Search.

## Features

-   **Free & Open Source**: No paid APIs, uses `duckduckgo-search`.
-   **Modern UI**: Clean, dark-mode interface inspired by premium web designs.
-   **Fast**: Built on FastAPI for high performance.
-   **Privacy-Focused**: Inherits DuckDuckGo's privacy benefits.

## Prerequisites

-   Python 3.8+
-   pip

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Run the server:
    ```bash
    python main.py
    ```
    Or with uvicorn directly:
    ```bash
    uvicorn main:app --reload
    ```

2.  Open your browser and navigate to `http://localhost:8000`.

3.  Enter your query and search!

## Project Structure

-   `main.py`: The FastAPI application and search logic.
-   `templates/`: HTML templates (`index.html`, `results.html`).
-   `static/`: CSS styles (`style.css`).
-   `requirements.txt`: Project dependencies.

## License

MIT
