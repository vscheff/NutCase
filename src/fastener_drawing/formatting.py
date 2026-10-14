"""Consistent measured-value precision for the picker and native dimensions."""
import math


DECIMAL_PLACES = {"deg": 1, "mm": 2, "in": 3}


def decimal_places(units):
    """Maximum displayed decimal places for a reported unit."""
    return DECIMAL_PLACES.get(str(units).strip().lower(), 2)


def format_measurement(value, units):
    """Round to the unit's display precision and trim insignificant zeros."""
    if value is None:
        return "Unresolved"
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("A displayed measurement must be finite")
    places = decimal_places(units)
    result = f"{number:.{places}f}"
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if result in ("-0", "") else result


def native_number_format(units):
    """FreeCAD TechDraw's native fixed precision format with zero trimming."""
    return f"%.{decimal_places(units)}w"


def dimension_format_spec(units, prefix="", suffix=""):
    return prefix + native_number_format(units) + suffix
