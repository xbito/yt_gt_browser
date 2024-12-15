# yt_gt_browser

A YouTube videos from Google Tasks browser.

In my Google Tasks lists, I have recorded several tasks that mention YouTube video URLs in either the Title or the Description, with the idea of watching them later. Some have extra text, but some are just the URL.

This app will let you visualize those so you can finally decide what to watch next! Forget about the algorithm. Why use the YouTube Watch Later playlist when you can build your own software to decide what to watch next!

## Features

- **YouTube Video Extraction**: Extract YouTube URLs from your Google Tasks.
- **OAuth 2.0 Authentication**: Securely authenticate with your Google account.
- **Dark Mode**: Toggle between light and dark themes.
- **Video Details**: Fetch and display video details such as title, thumbnail, channel, duration, and published date.
- **Sorting Options**: Sort tasks by Alphabetical, Task List, Duration, Channel, or Shuffle.
- **Stats Display**: Show total number of videos and total duration.

## Requirements

- Python 3.7+
- The following Python packages:
  - nicegui
  - google-api-python-client
  - google-auth-oauthlib
  - python-dateutil

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/yt_gt_browser.git
    cd yt_gt_browser
    ```

2. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Create a Google Cloud project and enable the Google Tasks API and YouTube Data API.

4. Create OAuth 2.0 Client ID credentials and download the `client_secrets.json` file.

5. Place the `client_secrets.json` file in the root directory of the project.

## Usage

1. Run the application:
    ```sh
    python main.py
    ```

2. Open your web browser and go to `http://localhost:8080`.

3. Authenticate with your Google account.

4. Browse and manage your YouTube videos from Google Tasks.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.