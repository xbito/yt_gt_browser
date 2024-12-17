"""
YouTube Tasks Browser application main module.

This module provides the core functionality for authenticating with Google APIs
and managing the interaction between Google Tasks and YouTube data.
"""

# Google API client is not liked by pylint
# pylint: disable=maybe-no-member

import re
import pickle
from pathlib import Path
from random import shuffle

from nicegui import ui
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GRequest
from googleapiclient.discovery import build
from starlette.responses import RedirectResponse
from fastapi import Request

from app_ui import show_login_ui, show_main_ui

# OAuth 2.0 configuration
SCOPES = [
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class App:
    """
    Main application class handling authentication and API interactions.

    Manages Google OAuth2 credentials, authentication flow, and provides
    methods for fetching and processing tasks and YouTube video data.
    """

    def __init__(self):
        self.credentials = None  # Single source of truth for credentials
        self.client_secrets_path = Path("client_secrets.json")
        self.auth_flow = None
        self.credentials_path = Path("stored_credentials.pickle")
        self._load_stored_credentials()
        self.dark_mode = False  # Add dark mode state

    def toggle_dark_mode(self):
        """Toggle dark mode state."""
        print("Toggling dark mode: ", self.dark_mode)
        self.dark_mode = not self.dark_mode
        ui.dark_mode(self.dark_mode)

    def _load_stored_credentials(self):
        """Load stored credentials and refresh if needed."""
        try:
            if self.credentials_path.exists():
                with open(self.credentials_path, "rb") as f:
                    credentials = pickle.load(f)

                if credentials and credentials.expired and credentials.refresh_token:
                    print("Refreshing expired credentials")
                    credentials.refresh(GRequest())
                    self._save_credentials(credentials)

                self.credentials = credentials
                print(
                    f"Loaded credentials, valid: {bool(credentials and not credentials.expired)}"
                )
        except Exception as e:
            print(f"Error loading credentials: {e}")
            self.credentials_path.unlink(missing_ok=True)
            self.credentials = None

    def _save_credentials(self, credentials):
        """Save credentials to file."""
        if credentials:
            print("Saving credentials")
            with open(self.credentials_path, "wb") as f:
                pickle.dump(credentials, f)

    def has_client_secrets(self):
        """Check if client_secrets.json file exists."""
        return self.client_secrets_path.exists()

    def is_authenticated(self):
        """Check if user is authenticated."""
        return bool(
            self.credentials and not self.credentials.expired and self.credentials.valid
        )

    async def authenticate(self):
        if not self.has_client_secrets():
            ui.notify("Missing client_secrets.json file", type="negative")
            return

        self.auth_flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=SCOPES,
            redirect_uri="http://localhost:8080/oauth2callback",
        )
        auth_url, _ = self.auth_flow.authorization_url(
            prompt="consent",
            access_type="offline",  # Enable refresh tokens
            include_granted_scopes="true",
        )
        ui.notify("Redirecting to Google for authentication", type="info")
        ui.run_javascript(f"window.location.href = '{auth_url}'")

    def extract_youtube_urls(self, text):
        """Extract YouTube URLs from text."""
        if not text:
            return []

        # Match various YouTube URL formats
        youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)"
        return re.findall(youtube_regex, text)

    async def fetch_tasks_with_videos(self):
        """Fetch all tasks and extract ones with YouTube URLs."""
        if not self.credentials:
            return []

        service = build("tasks", "v1", credentials=self.credentials)
        tasks_with_videos = []

        # Get all task lists with pagination
        tasklists = []
        page_token = None
        while True:
            response = service.tasklists().list(pageToken=page_token).execute()
            tasklists.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        for tasklist in tasklists:
            # Get all tasks in the task list with pagination
            page_token = None
            while True:
                response = (
                    service.tasks()
                    .list(
                        tasklist=tasklist["id"], showHidden=True, pageToken=page_token
                    )
                    .execute()
                )
                tasks = response.get("items", [])
                for task in tasks:
                    if task.get("status") == "completed":
                        continue

                    youtube_urls = []

                    # Check title and notes for YouTube URLs
                    youtube_urls.extend(
                        self.extract_youtube_urls(task.get("title", ""))
                    )
                    youtube_urls.extend(
                        self.extract_youtube_urls(task.get("notes", ""))
                    )

                    if youtube_urls:
                        tasks_with_videos.append(
                            {
                                "task_list": tasklist["title"],
                                "task_list_id": tasklist["id"],
                                "task_id": task["id"],
                                "task_url": task.get("webViewLink", ""),
                                "task_title": task.get("title", ""),
                                "task_notes": task.get("notes", ""),
                                "youtube_ids": youtube_urls,
                                "status": task.get("status", ""),
                                "due": task.get("due", ""),
                            }
                        )
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
        return tasks_with_videos

    async def get_video_details(self, video_ids):
        """Fetch video details from YouTube API."""
        if not self.credentials or not video_ids:
            return {}

        youtube = build("youtube", "v3", credentials=self.credentials)
        video_details = {}

        # Process videos in batches of 50 (API limit)
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            request = youtube.videos().list(
                part="snippet,contentDetails", id=",".join(batch)
            )
            response = request.execute()

            for item in response.get("items", []):
                video_details[item["id"]] = {
                    "title": item["snippet"]["title"],
                    "thumbnail": item["snippet"]["thumbnails"]["medium"],
                    "channel": item["snippet"]["channelTitle"],
                    "channelId": item["snippet"]["channelId"],  # Add channelId
                    "duration": item["contentDetails"]["duration"],
                    "publishedAt": item["snippet"]["publishedAt"],
                }

        return video_details


def sort_tasks(tasks, video_details, criteria):
    """
    Sort tasks based on specified criteria.

    Args:
        tasks: List of task dictionaries containing video information
        video_details: Dictionary of video details keyed by video ID
        criteria: String indicating sort criteria ('Alphabetical', 'Task List',
                'Duration', 'Channel', or 'Shuffle')
    """
    if criteria == "Alphabetical":
        tasks.sort(key=lambda task: task["task_title"].lower())
    elif criteria == "Task List":
        tasks.sort(key=lambda task: task["task_list"].lower())
    elif criteria == "Duration":
        tasks.sort(
            key=lambda task: sum(
                int(
                    re.match(
                        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
                        video_details[vid]["duration"],
                    ).group(1)
                    or 0
                )
                * 3600
                + int(
                    re.match(
                        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
                        video_details[vid]["duration"],
                    ).group(2)
                    or 0
                )
                * 60
                + int(
                    re.match(
                        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
                        video_details[vid]["duration"],
                    ).group(3)
                    or 0
                )
                for vid in task["youtube_ids"]
            )
        )
    elif criteria == "Channel":
        tasks.sort(
            key=lambda task: video_details[task["youtube_ids"][0]]["channel"].lower()
        )
    elif criteria == "Shuffle":
        shuffle(tasks)


def logout():
    """Handle user logout."""
    if app.credentials_path.exists():
        app.credentials_path.unlink()
    app.credentials = None
    ui.navigate.reload()


app = App()


@ui.page("/")
async def main():
    """
    Main application route handler.

    Displays either the login UI or main application interface based on
    authentication status.
    """
    print("Test Is Authenticate? ", app.is_authenticated())
    if app.is_authenticated():
        await show_main_ui(app)
    else:
        show_login_ui(app)


@ui.page("/oauth2callback")
def oauth2callback(request: Request):
    """
    OAuth2 callback handler for Google authentication.

    Args:
        request: FastAPI request object containing OAuth2 response data

    Returns:
        RedirectResponse: Redirects to main page after handling authentication
    """
    print("\n=== OAuth2 Callback Started ===")
    try:
        params = request.query_params
        code = params.get("code")
        if code:
            print(f"Received auth code: {code[:10]}...")
        else:
            print("No code received!")

        if not app.auth_flow:
            print("Error: Authentication flow not initialized")
            return RedirectResponse("/")

        print("Exchanging code for credentials...")
        app.auth_flow.fetch_token(code=code)
        credentials = app.auth_flow.credentials
        print(f"Credentials obtained, valid: {credentials.valid}")

        app._save_credentials(credentials)
        app.credentials = credentials
        app.auth_flow = None

        print("Authentication completed successfully")
        return RedirectResponse("/")
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        print(f"Error type: {type(e)}")
        return RedirectResponse("/")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="YouTube Videos from Google Tasks")
