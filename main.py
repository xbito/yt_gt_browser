"""
YouTube Tasks Browser application main module.

This module provides the core functionality for authenticating with Google APIs
and managing the interaction between Google Tasks and YouTube data.
"""

# Google API client is not liked by pylint
# pylint: disable=maybe-no-member

import re
import pickle
import base64
from pathlib import Path
import os
import dotenv

import dotenv
from nicegui import ui, app as ng_app
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
                    self.save_credentials(credentials)

                self.credentials = credentials
                print(
                    f"Loaded credentials, valid: {bool(credentials and not credentials.expired)}"
                )
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error loading credentials: {e}")
            self.credentials_path.unlink(missing_ok=True)
            self.credentials = None

    def save_credentials(self, credentials):
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

    async def authenticate(self, request: Request = None):
        """
        Initiate OAuth2 authentication flow.

        Args:
            request: FastAPI request object to determine the current host
        """
        if not self.has_client_secrets():
            ui.notify("Missing client_secrets.json file", type="negative")
            return

        # Determine the base URL from the request, fallback to localhost
        if request:
            base_url = str(request.base_url).rstrip("/")
        else:
            base_url = "http://localhost:8080"

        redirect_uri = f"{base_url}/oauth2callback"
        print(f"Redirect URI: {redirect_uri}")

        self.auth_flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, _ = self.auth_flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true",
        )
        ui.notify("Redirecting to Google for authentication", type="info")
        ui.navigate.to(f"{auth_url}")

    def extract_youtube_urls(self, text):
        """Extract YouTube URLs from text."""
        if not text:
            return []

        # Match various YouTube URL formats
        youtube_regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)"  # pylint: disable=line-too-long
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


app = App()


def store_credentials_in_browser(credentials):
    """
    Store current credentials in local storage as base64-encoded pickle.
    Note: This can be a security risk. Use carefully.
    """
    data = pickle.dumps(credentials)
    encoded = base64.b64encode(data).decode("utf-8")
    ng_app.storage.browser["yt_credentials"] = encoded
    print("Stored credentials in browser local storage.")


def load_credentials_from_browser():
    """
    Load credentials from local storage if present.
    Returns:
        Credentials object or None if not found
    """
    encoded = ng_app.storage.browser.get("yt_credentials", None)
    if encoded:
        data = base64.b64decode(encoded.encode("utf-8"))
        loaded = pickle.loads(data)
        print("Loaded credentials from browser local storage.")
        return loaded
    return None


@ui.page("/")
async def main(request: Request):
    """
    Main application route handler.

    Displays either the login UI or main application interface based on
    authentication status.
    """
    # Try loading from browser storage if we don't have valid credentials
    if not (app.credentials and app.is_authenticated()):
        retrieved = load_credentials_from_browser()
        print("Retrieved credentials from browser storage: ", retrieved)
        if retrieved and not retrieved.expired and retrieved.valid:
            print("Using retrieved credentials")
            app.credentials = retrieved
        else:
            print("No valid credentials found")

    print("Test Is Authenticate? ", app.is_authenticated())
    if app.is_authenticated():
        await show_main_ui(app)
    else:
        await show_login_ui(app, request)


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

        app.save_credentials(credentials)
        app.credentials = credentials
        app.auth_flow = None

        # Store credentials in local storage so a server restart won't break user session
        store_credentials_in_browser(credentials)

        print("Authentication completed successfully")
        return RedirectResponse("/")
    except Exception as e:  # pylint: disable=broad-except
        print(f"Authentication error: {str(e)}")
        print(f"Error type: {type(e)}")
        return RedirectResponse("/")


if __name__ in {"__main__", "__mp_main__"}:
    # Step 1) Load environment variables
    dotenv.load_dotenv()

    # Step 2) Check for STORAGE_SECRET in environment
    secret = os.getenv("STORAGE_SECRET")

    # Step 3) If not found, read from file
    if not secret:
        secret_file = Path("credentials") / "storage_secret"
        if secret_file.exists():
            secret = secret_file.read_text().strip()

    # Step 4) Pass the secret into ui.run(...)
    ui.run(title="YouTube Videos from Google Tasks", storage_secret=secret)
