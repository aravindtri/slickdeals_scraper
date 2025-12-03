# Slickdeals Scraper & AI Chat

A powerful tool to scrape Slickdeals threads, save them locally, and chat with the data using Google Gemini AI.

## Features

*   **Scrape Comments**: Fetches comments from any Slickdeals thread URL.
*   **Pagination Support**: Automatically scrapes multiple pages.
*   **Duplicate Detection**: Avoids saving duplicate comments.
*   **AI Chat**: Chat with the scraped data using Google Gemini (Flash 2.0).
*   **Token Optimization**: Summarizes threads to save on AI token usage.
*   **Local Storage**: Saves deals as JSON files for offline access.
*   **Dockerized**: Easy to deploy using Docker.

## Prerequisites

*   [Docker Desktop](https://www.docker.com/products/docker-desktop/)
*   A Google Gemini API Key (Get one [here](https://aistudio.google.com/app/apikey))

## Quick Start

1.  **Clone the repository**
    ```bash
    git clone <your-repo-url>
    cd slickdeals_scraper
    ```

2.  **Set up your API Key**
    Create a `.env` file in the root directory and add your Google API Key:
    ```
    GOOGLE_API_KEY=your_actual_api_key_here
    ```

3.  **Run with Docker**
    ```bash
    docker-compose up --build
    ```

4.  **Access the App**
    Open your browser and go to: `http://localhost:8000`

## Configuration

You can configure the application using environment variables in `docker-compose.yml` or a `.env` file.

*   `GOOGLE_API_KEY`: Your Google Gemini API Key.
*   `GEMINI_MODEL`: The Gemini model to use for chat and summarization. Default is `gemini-2.0-flash`.

### Available Models

You can use any of the following model names for `GEMINI_MODEL`. Note that model availability may vary by region and API access level.

**Gemini 3 (Preview)**
*   `gemini-3-pro-preview`
*   `gemini-3-pro-image-preview`

**Gemini 2.5 (Latest/Preview)**
*   `gemini-2.5-flash`
*   `gemini-2.5-pro`
*   `gemini-2.5-flash-lite`
*   `gemini-2.5-flash-image`
*   `gemini-2.5-flash-image-preview`
*   `gemini-2.5-flash-preview-tts`
*   `gemini-2.5-pro-preview-tts`
*   `gemini-2.5-flash-preview-09-2025`
*   `gemini-2.5-flash-lite-preview-09-2025`
*   `gemini-2.5-computer-use-preview-10-2025`

**Gemini 2.0**
*   `gemini-2.0-flash` (Default)
*   `gemini-2.0-flash-lite`
*   `gemini-2.0-pro-exp`
*   `gemini-2.0-flash-exp`
*   `gemini-2.0-flash-001`
*   `gemini-2.0-flash-lite-001`
*   `gemini-2.0-flash-lite-preview`
*   `gemini-2.0-flash-lite-preview-02-05`
*   `gemini-2.0-pro-exp-02-05`
*   `gemini-2.0-flash-exp-image-generation`
*   `learnlm-2.0-flash-experimental`

**Gemini 1.5 & Aliases**
*   `gemini-flash-latest`
*   `gemini-flash-lite-latest`
*   `gemini-pro-latest`
*   `gemini-1.5-flash`
*   `gemini-1.5-pro`

**Gemma Models**
*   `gemma-3-1b-it`
*   `gemma-3-4b-it`
*   `gemma-3-12b-it`
*   `gemma-3-27b-it`
*   `gemma-3n-e4b-it`
*   `gemma-3n-e2b-it`

**Experimental / Other**
*   `gemini-exp-1206`
*   `nano-banana-pro-preview`
*   `gemini-robotics-er-1.5-preview`

## Usage

1.  **Paste a URL**: Copy a Slickdeals thread URL (e.g., `https://slickdeals.net/f/12345...`).
2.  **Scrape**: Click "Scrape Comments". The data will be saved locally.
3.  **Chat**: Click "Chat with this Data" to ask questions about the deal, user sentiment, or specific details.

## Project Structure

*   `app.py`: Main FastAPI backend application.
*   `index.html`: Frontend user interface.
*   `scraped_data/`: Directory where scraped JSON files are stored (persisted via Docker volume).
*   `Dockerfile`: Container definition.

## License

MIT
