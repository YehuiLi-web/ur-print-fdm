"""Utility functions for the UR5 Fiber Printer Studio."""

from ur_print_fdm.shared.net import is_valid_ip

def parse_array_input(input_text):
    """Parse array input from text field to list of floats"""
    if not input_text.strip():
        return None

    try:
        # Handle different possible formats (comma separated, space separated, mixed)
        values = []
        # Split by commas first
        for part in input_text.split(','):
            # Then split by spaces
            for subpart in part.split():
                if subpart.strip():
                    values.append(float(subpart.strip()))
        return values
    except (ValueError, TypeError):
        # Try alternative parsing
        try:
            # Attempt to evaluate as Python list
            import ast
            parsed = ast.literal_eval(input_text)
            if isinstance(parsed, list):
                return [float(x) for x in parsed]
            else:
                return None
        except:
            return None

__all__ = ["parse_array_input", "is_valid_ip"]
