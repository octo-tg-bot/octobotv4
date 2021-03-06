import logging
import threading

from octobot.classes.catalog import CatalogPhoto
thread_local = threading.local()

def add_photo_to_text(text, photo_url):
    if not isinstance(photo_url, list):
        photo_url = [photo_url]
    photos = ""
    for photo in photo_url:
        if isinstance(photo, CatalogPhoto):
            photo = photo.url
        photos += f'<a href="{photo}">\u200b</a>'
    text = photos + text
    return text


def generate_edit_id(message):
    return f"emsg:{message.chat.id}:{message.message_id}"


def path_to_module(path: str):
    return path.replace("\\", "/").replace("/", ".").replace(".py", "")


class AddContextDataToLoggingRecord(logging.Filter):

    def filter(self, record):
        ctx: "Context" = getattr(thread_local, "current_context", None)
        if ctx is not None:
            record.update_type = ctx.update_type
            if ctx.chat:
                record.chat_name = ctx.chat.title
            record.called_command = ctx.called_command
        else:
            record.context_not_available = True
        return True
