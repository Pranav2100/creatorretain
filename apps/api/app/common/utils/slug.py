import re


def generate_slug(text: str) -> str:
    """
    Convert text into a URL-friendly slug.

    Example:
        Strange Live -> strange-live
        Mr. Beast! -> mr-beast
    """

    text = text.strip().lower()

    text = re.sub(r"[^a-z0-9\s-]", "", text)

    text = re.sub(r"\s+", "-", text)

    text = re.sub(r"-+", "-", text)

    return text