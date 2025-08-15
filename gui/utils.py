import yaml
import math
import colorsys


def load_config(config_path):
    """Load configuration file"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def save_config(config_path, config_data):
    """Save configuration file with readable formatting"""
    # Setup YAML formatting
    class OrderedDumper(yaml.SafeDumper):
        pass
        
    def represent_list(dumper, data):
        """Format list elements with proper indentation"""
        # Special case for connection lists: use flow style [x, y] for 2-integer lists
        if len(data) == 2 and all(isinstance(x, int) for x in data):
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True)
        return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=False)
        
    def represent_dict(dumper, data):
        """Format dictionary entries with proper indentation"""
        return dumper.represent_mapping('tag:yaml.org,2002:map', data, flow_style=False)
    
    # Register list and dict representation methods
    OrderedDumper.add_representer(list, represent_list)
    OrderedDumper.add_representer(dict, represent_dict)
    
    # Write config file with structured formatting
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(
            config_data, 
            f, 
            Dumper=OrderedDumper, 
            default_flow_style=False,
            sort_keys=False,
            indent=2,
            allow_unicode=True,
            width=120
        )


def generate_color(index, total_points):
    """Generate a smooth color gradient for keypoints using colorsys"""
    # Handle edge case
    if total_points <= 1:
        return [0, 0, 255]  # Red in BGR
    
    # Create smooth gradient effect
    position = index / max(total_points - 1, 1)
    
    # Use a narrower hue range (0-200 degrees) for subtle color changes
    hue = position * 200 / 360  # Convert to 0-1 range for colorsys
    saturation = 0.85
    value = 0.95
    
    # Convert HSV to RGB using Python's built-in colorsys
    r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
    
    # Return BGR format for OpenCV compatibility
    return [int(b * 255), int(g * 255), int(r * 255)] 