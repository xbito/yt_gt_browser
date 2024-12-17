from nicegui import ui
from random import shuffle
import re
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parse_date

def create_video_card(video_info, task_info):
    """Create a card displaying video and task information."""
    with ui.card().classes("w-full max-w-sm"):
        # Thumbnail section
        ui.image(video_info["thumbnail"]["url"]).classes("w-full")

        # Content section
        with ui.column().classes("p-4 gap-2"):
            # Video title
            ui.link(
                text=video_info["title"],
                target=f'https://youtube.com/watch?v={task_info["youtube_ids"][0]}',
            ).classes("font-bold flex-grow")

            # Video details
            with ui.column().classes("gap-1 text-sm"):
                with ui.row():
                    ui.label("Channel: ")
                    ui.link(
                        text=video_info["channel"],
                        target=f'https://www.youtube.com/channel/{video_info["channelId"]}',
                    )
                ui.label(f'Duration: {parse_duration(video_info["duration"])}')
                ui.label(f'Published: {relative_time(video_info["publishedAt"])}')
                ui.separator()
                ui.label(f'Task List: {task_info["task_list"]}')

                # Link to Google Tasks (opens in new tab)
                with ui.row().classes("items-center gap-1"):
                    ui.icon("task_alt")
                    ui.link(
                        text="Open in Google Tasks",
                        target=f"https://tasks.google.com/embed/?origin=https://calendar.google.com&fullWidth=1",
                    ).tooltip("Open in Google Tasks")

def show_credentials_instructions():
    with ui.column().classes("w-full items-center justify-center gap-4"):
        ui.label("Missing Google Cloud Credentials").classes("text-h4")
        with ui.card().classes("max-w-2xl"):
            ui.label("To use this application, you need to:").classes("text-bold")
            with ui.column().classes("ml-4 gap-2"):
                ui.label(
                    "1. Go to Google Cloud Console (https://console.cloud.google.com)"
                )
                ui.label("2. Create a new project or select an existing one")
                ui.label("3. Enable the Google Tasks API and YouTube Data API")
                ui.label("4. Go to APIs & Services > Credentials")
                ui.label("5. Create OAuth 2.0 Client ID credentials")
                ui.label("6. Download the client secrets file")
                ui.label(
                    '7. Save it as "client_secrets.json" in the same folder as this application'
                )
            ui.button("Refresh", on_click=lambda: ui.refresh()).classes("mt-4")

def show_login_ui(app):
    if not app.has_client_secrets():
        show_credentials_instructions()
    else:
        with ui.column().classes("w-full items-center justify-center"):
            ui.label("YouTube Videos from Google Tasks").classes("text-h4 mb-4")
            ui.label("Please log in to continue").classes("mb-4")
            ui.button("Login with Google", on_click=app.authenticate).classes(
                "bg-blue-500 text-white"
            )
            ui.button("Toggle Dark Mode", on_click=app.toggle_dark_mode).classes(
                "mt-4"
            )  # Add dark mode toggle button

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

async def show_main_ui(app):
    """Display the main UI with video tasks."""
    with ui.column().classes("w-full max-w-7xl mx-auto p-4"):
        ui.label("YouTube Videos from Google Tasks").classes("text-h4 mb-4 text-center")

        with ui.row().classes("w-full justify-between items-center mb-4 gap-4"):
            with ui.row().classes("gap-2"):
                ui.button("Refresh", on_click=lambda: ui.refresh()).classes(
                    "bg-blue-500 text-white"
                )
                ui.button("Logout", on_click=lambda: logout()).classes(
                    "bg-red-500 text-white"
                )
                ui.button("Toggle Dark Mode", on_click=app.toggle_dark_mode).classes(
                    "bg-gray-500 text-white"
                )  # Add dark mode toggle button

            sorting_criteria = ui.select(
                options=["Alphabetical", "Task List", "Duration", "Channel", "Shuffle"],
                value="Alphabetical",
                label="Sort by",
            ).classes("mb-4")

        # Loading indicator
        loading = ui.spinner("dots", size="lg")

        try:
            # Fetch tasks with videos
            tasks = await app.fetch_tasks_with_videos()

            if not tasks:
                ui.label("No YouTube videos found in your tasks").classes(
                    "text-lg text-center w-full"
                )
                return

            # Get unique video IDs
            video_ids = list(set(vid for task in tasks for vid in task["youtube_ids"]))

            # Fetch video details
            video_details = await app.get_video_details(video_ids)

            # Calculate stats
            total_videos = len(video_ids)
            total_duration_seconds = sum(
                [
                    int(
                        re.match(
                            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", video["duration"]
                        ).group(1)
                        or 0
                    )
                    * 3600
                    + int(
                        re.match(
                            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", video["duration"]
                        ).group(2)
                        or 0
                    )
                    * 60
                    + int(
                        re.match(
                            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", video["duration"]
                        ).group(3)
                        or 0
                    )
                    for video in video_details.values()
                ]
            )
            total_duration = format_duration(total_duration_seconds)

            # Display stats
            with ui.row().classes("w-full justify-center mb-4 gap-4"):
                ui.label(
                    f"Total Videos: {total_videos} | Total Duration: {total_duration}"
                ).classes("text-lg")

            # Sort tasks based on selected criteria
            sort_tasks(tasks, video_details, sorting_criteria.value)

            # Create grid for video cards
            with ui.grid().classes(
                "w-full gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            ):
                for task in tasks:
                    for video_id in task["youtube_ids"]:
                        if video_id in video_details:
                            create_video_card(video_details[video_id], task)

        except Exception as e:
            ui.notify(f"Error loading videos: {str(e)}", type="negative")
        finally:
            loading.delete()

        # Add footer with repository link
        with ui.row().classes("w-full justify-center mt-8"):
            ui.link(
                text="View on GitHub",
                target="https://github.com/xbito/yt_gt_browser",
            ).classes("text-blue-500 underline")

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
