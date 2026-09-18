"""Turns a short user request into a richer prompt for the image model."""

# Presets are phrased to complement the sketch styling that ImageGenerator
# appends automatically, instead of fighting it.
STYLE_PRESETS = {
    "blueprint": "annotated like a technical blueprint, measurements and labels",
    "storyboard": "framed like a storyboard panel, dynamic composition, motion lines",
    "patent": "in the style of a vintage patent drawing, numbered parts",
}

DEFAULT_STYLE = "blueprint"


def build_prompt(prompt: str, style: str | None = None) -> str:
    """Combine the user's subject with a style preset."""
    preset = STYLE_PRESETS.get(style or DEFAULT_STYLE, STYLE_PRESETS[DEFAULT_STYLE])
    return f"{prompt}, {preset}"
