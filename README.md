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
