import os
from pathlib import Path
def load_config(filename='config.txt'):
    SCRIPT_DIR = Path(__file__).resolve().parent
    config_file = SCRIPT_DIR / filename
    """
    Loads a configuration file and returns a dictionary of settings.

    Args:
        filepath (str): The path to the configuration file.

    Returns:
        dict: A dictionary containing the configuration settings,
              or None if the file cannot be found.
    """
    # Check if the configuration file exists
    if not os.path.exists(config_file):
        print(f"Error: Configuration file not found at '{config_file}'")
        return None

    # Initialize an empty dictionary to store settings
    settings = {}
    
    print(f"Reading configuration from '{config_file}'...")

    try:
        # Open the file for reading
        with open(config_file, 'r') as f:
            # Read the file line by line
            for line in f:
                # Strip leading/trailing whitespace from the line
                line = line.strip()

                # Ignore empty lines and lines that start with '#' (comments)
                if not line or line.startswith('#'):
                    continue

                # Split the line into key and value at the first '=' sign
                if '=' in line:
                    key, value = line.split('=', 1)
                    
                    # Strip whitespace from the key and value
                    key = key.strip()
                    value = value.strip()
                    
                    # Store the key-value pair in the settings dictionary
                    settings[key] = value
                else:
                    print(f"Warning: Skipping malformed line: '{line}'")
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return None
        
    print("Configuration loaded successfully.")
    return settings


def save_config_setting(key, value, filename='config.txt'):
    """
    Sets or updates a configuration setting in the specified file.
    
    The function preserves the order of existing settings, comments, 
    and empty lines. If the key does not exist, it is added to the 
    end of the file.

    Args:
        key (str): The configuration key to set.
        value (str): The new value for the configuration key.
        filename (str): The name of the configuration file.
    
    Returns:
        bool: True if the setting was saved successfully, False otherwise.
    """
    SCRIPT_DIR = Path(__file__).resolve().parent
    config_file = SCRIPT_DIR / filename
    
    key_str = key.strip()
    value_str = str(value).strip()
    new_line = f"{key_str} = {value_str}\n"
    key_found = False
    lines = []
    
    print(f"Attempting to set '{key_str}' to '{value_str}' in '{config_file}'...")

    try:
        # Read all lines from the file if it exists
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                lines = f.readlines()
        
        updated_lines = []
        # Iterate over lines to find and update the key
        for line in lines:
            stripped_line = line.strip()
            
            # Check for empty lines or comments
            if not stripped_line or stripped_line.startswith('#'):
                updated_lines.append(line)
                continue
            
            # Check if the line contains a key-value pair
            if '=' in stripped_line:
                current_key, current_value = stripped_line.split('=', 1)
                
                if current_key.strip() == key_str:
                    # Key found, replace the line with the new key-value pair
                    updated_lines.append(new_line)
                    key_found = True
                    print(f"Key '{key_str}' updated.")
                    continue
            
            # Keep other lines as is
            updated_lines.append(line)

        # If the key was not found, append the new setting to the end
        if not key_found:
            # Add a newline if the file wasn't empty and didn't end with one
            if lines and not lines[-1].endswith('\n'):
                updated_lines.append('\n')
            updated_lines.append(new_line)
            print(f"Key '{key_str}' added to the end of the file.")
            
        # Write the updated content back to the file
        with open(config_file, 'w') as f:
            f.writelines(updated_lines)

        print("Configuration file saved successfully.")
        return True

    except Exception as e:
        print(f"An error occurred while writing to the file: {e}")
        return False