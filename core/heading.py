"""Heading/direction utilities."""


def degrees_to_compass(degrees: float) -> str:
    """
    Convert degrees (0-360) to compass direction text.

    Args:
        degrees: Heading in degrees (0 = north, 90 = east, etc.)

    Returns:
        Compass direction like "north", "north-east", "south-west", etc.
    """
    if degrees is None:
        return "unknown"

    # Normalize to 0-360
    degrees = degrees % 360

    # 16-point compass with 22.5 degree segments
    directions = [
        "north",
        "north-north-east",
        "north-east",
        "east-north-east",
        "east",
        "east-south-east",
        "south-east",
        "south-south-east",
        "south",
        "south-south-west",
        "south-west",
        "west-south-west",
        "west",
        "west-north-west",
        "north-west",
        "north-north-west",
    ]

    # Each segment is 22.5 degrees, offset by 11.25 to center on direction
    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]


def degrees_to_compass_short(degrees: float) -> str:
    """
    Convert degrees to short compass direction (8-point).

    Args:
        degrees: Heading in degrees

    Returns:
        Short direction like "N", "NE", "SW", etc.
    """
    if degrees is None:
        return "?"

    degrees = degrees % 360

    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]


def degrees_to_compass_8point(degrees: float) -> str:
    """
    Convert degrees to 8-point compass direction text.

    Args:
        degrees: Heading in degrees

    Returns:
        Direction like "north", "north-east", "south-west", etc.
    """
    if degrees is None:
        return "unknown"

    degrees = degrees % 360

    directions = [
        "north",
        "north-east",
        "east",
        "south-east",
        "south",
        "south-west",
        "west",
        "north-west",
    ]
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]
