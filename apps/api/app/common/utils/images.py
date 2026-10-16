"""
Deciding whether some bytes are an image we are willing to serve.

The browser's declared content type is not evidence - it is a
string the client chose - so everything here works from the bytes
themselves.
"""

__all__ = [
    "MAX_IMAGE_BYTES",
    "ImageRejected",
    "sniff_image",
]

# Generous for a logo and small enough that a stray video or a
# RAW photo is refused before it reaches storage.
MAX_IMAGE_BYTES = 2 * 1024 * 1024

# Extension is for the stored filename only; nothing is trusted to
# the name.
_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
)


class ImageRejected(ValueError):
    """Not something we will store or serve."""


def sniff_image(data: bytes) -> tuple[str, str]:
    """
    The real content type and file extension, or a refusal.

    SVG is deliberately absent from the accepted list. It is a
    genuine image format, and it is also a document that can carry
    script: serving a creator-supplied SVG from our own origin
    would hand whoever uploaded it the ability to run code as
    anyone who views the page. There is no flag for "safe SVG"
    short of parsing and rewriting it, so it is simply not allowed.
    """
    if not data:
        raise ImageRejected("That file is empty.")

    if len(data) > MAX_IMAGE_BYTES:
        megabytes = MAX_IMAGE_BYTES // (1024 * 1024)
        raise ImageRejected(
            f"Images have to be under {megabytes}MB."
        )

    for signature, content_type, extension in _SIGNATURES:
        if data.startswith(signature):
            return content_type, extension

    # RIFF....WEBP - the length sits between the two markers.
    if (
        len(data) >= 12
        and data[:4] == b"RIFF"
        and data[8:12] == b"WEBP"
    ):
        return "image/webp", "webp"

    if _looks_like_svg(data):
        raise ImageRejected(
            "SVG files are not accepted. Use a PNG, JPEG or WebP."
        )

    raise ImageRejected(
        "That does not look like an image. Use a PNG, JPEG, "
        "GIF or WebP."
    )


def _looks_like_svg(data: bytes) -> bool:
    """
    Only so the refusal can say something useful. An SVG may open
    with a declaration, a comment or whitespace before the tag, so
    this checks the opening rather than the very first byte.
    """
    head = data[:512].lstrip().lower()

    return head.startswith(b"<?xml") or head.startswith(b"<svg")
