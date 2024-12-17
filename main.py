from nicegui import ui, app as nicegui_app  # Add import for app
from nicegui.elements.mixins.value_element import ValueElement
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pathlib import Path
import os
import re
from urllib.parse import parse_qs, urlparse
import pickle
from datetime import datetime, timedelta, timezone  # Add timezone import
from starlette.responses import RedirectResponse
from google.auth.transport.requests import Request as GRequest
from fastapi import Request
from random import shuffle
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parse_date

from app_ui import show_login_ui, show_main_ui, create_video_card, show_credentials_instructions

# OAuth 2.0 configuration
SCOPES = [
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class App:
    def __init__(self):
        self.credentials = None  # Single source of truth for credentials
        self.client_secrets_path = Path("client_secrets.json")
        self._flow = None
        self.credentials_path = Path("stored_credentials.pickle")
        self._load_stored_credentials()
        self.dark_mode = False  # Add dark mode state

    def toggle_dark_mode(self):
        """Toggle dark mode state."""
        print("Toggling dark mode: ", self.dark_mode)
        self.dark_mode = not self.dark_mode
        dark = ui.dark_mode(self.dark_mode)

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
        return self.client_secrets_path.exists()

    def is_authenticated(self):
        return bool(
            self.credentials and not self.credentials.expired and self.credentials.valid
        )

    async def authenticate(self):
        if not self.has_client_secrets():
            ui.notify("Missing client_secrets.json file", type="negative")
            return

        self._flow = Flow.from_client_secrets_file(
            self.client_secrets_path,
            scopes=SCOPES,
            redirect_uri="http://localhost:8080/oauth2callback",
        )
        auth_url, _ = self._flow.authorization_url(
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

                    # Check title
                    youtube_urls.extend(
                        self.extract_youtube_urls(task.get("title", ""))
                    )

                    # Check notes
                    youtube_urls.extend(
                        self.extract_youtube_urls(task.get("notes", ""))
                    )

                    if youtube_urls:
                        tasks_with_videos.append(
                            {
                                "task_list": tasklist["title"],
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


def parse_duration(duration):
    """Convert ISO 8601 duration to human readable format."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if not match:
        return "Unknown"

    hours, minutes, seconds = match.groups()
    parts = []

    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")

    return " ".join(parts)


def relative_time(published_at):
    """Convert a datetime to a summarized relative time string."""
    now = datetime.now(timezone.utc)  # Make now offset-aware
    published_date = parse_date(published_at)
    delta = relativedelta(now, published_date)

    if delta.years > 0:
        return f"{delta.years} year{'s' if delta.years > 1 else ''} ago"
    elif delta.months > 0:
        return f"{delta.months} month{'s' if delta.months > 1 else ''} ago"
    elif delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    elif delta.hours > 0:
        return f"{delta.hours} hour{'s' if delta.hours > 1 else ''} ago"
    elif delta.minutes > 0:
        return f"{delta.minutes} minute{'s' if delta.minutes > 1 else ''} ago"
    else:
        return "just now"


def format_duration(total_seconds):
    """Convert total seconds to a simplified human-readable format."""
    hours, remainder = divmod(total_seconds, 3600)
    return f"{hours}+h" if remainder > 0 else f"{hours}h"


def sort_tasks(tasks, video_details, criteria):
    """Sort tasks based on the given criteria."""
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
    ui.refresh()


app = App()


@ui.page("/")
async def main():
    print("Test Is Authenticate? ", app.is_authenticated())
    if app.is_authenticated():
        await show_main_ui(app)
    else:
        show_login_ui(app)


@ui.page("/oauth2callback")
def oauth2callback(request: Request):
    print("\n=== OAuth2 Callback Started ===")
    try:
        params = request.query_params
        code = params.get("code")
        (
            print(f"Received auth code: {code[:10]}...")
            if code
            else print("No code received!")
        )

        if not app._flow:
            print("Error: Authentication flow not initialized")
            return RedirectResponse("/")

        print("Exchanging code for credentials...")
        app._flow.fetch_token(code=code)
        credentials = app._flow.credentials
        print(f"Credentials obtained, valid: {credentials.valid}")

        app._save_credentials(credentials)
        app.credentials = credentials
        app._flow = None

        print("Authentication completed successfully")
        return RedirectResponse("/")
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        print(f"Error type: {type(e)}")
        return RedirectResponse("/")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="YouTube Videos from Google Tasks", dark_mode=app.dark_mode)
