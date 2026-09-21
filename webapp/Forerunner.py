import subprocess
import time
import sys
import os # Import os for directory checks

# --- Configuration ---
# Command to run your Flask app.
# This should be a list of strings, where the first item is the command
# and subsequent items are the arguments.
#
# Your command 'sudo -E webapp/bin/python3 app.py' is split into:
FLASK_APP_COMMAND = ['sudo', '-E', 'webapp/bin/python3', 'app.py']

# Set the working directory for the Flask app.
# IMPORTANT: Change this to the directory where your command should be run from.
# For example: '/home/user/my_project'
FLASK_APP_DIRECTORY = '/home/azureuser/webapp' 
# ---------------------

def start_flask_app():
    """
    Starts the Flask app as a subprocess.
    Returns the process object.
    """
    print(f"[Monitor] Starting Flask app: {' '.join(FLASK_APP_COMMAND)}")
    
    app_cwd = FLASK_APP_DIRECTORY
    
    # Warning if the directory hasn't been changed from the placeholder
    if app_cwd == '/path/to/your/app_directory':
        print(f"[Monitor] WARNING: FLASK_APP_DIRECTORY is still set to the placeholder value.")
        print(f"[Monitor] Please edit monitor.py and set it to your app's working directory.")
        print(f"[Monitor] Defaulting to running from monitor's directory ('.').")
        app_cwd = '.' # Default to current directory
        
    # Check if the directory is valid
    if not os.path.isdir(app_cwd):
        print(f"[Monitor] ERROR: The specified FLASK_APP_DIRECTORY is not a valid directory: {app_cwd}")
        print(f"[Monitor] Please correct the path in monitor.py. Retrying in 5 seconds...")
        return None # Will trigger a retry in the main loop

    print(f"[Monitor] Using working directory: {os.path.abspath(app_cwd)}")

    # Use subprocess.Popen to run the app in a new, non-blocking process
    try:
        # 'cwd' sets the current working directory for the new process
        process = subprocess.Popen(FLASK_APP_COMMAND, cwd=app_cwd)
        print(f"[Monitor] Flask app started with PID: {process.pid}")
        return process
    except FileNotFoundError:
        # This error now means the *command* (e.g., 'sudo') wasn't found
        print(f"[Monitor] Error: Could not find the command '{FLASK_APP_COMMAND[0]}'.")
        print(f"[Monitor] Make sure '{FLASK_APP_COMMAND[0]}' is correct and in your system's PATH.")
        print(f"[Monitor] Full command: {' '.join(FLASK_APP_COMMAND)}")
        print(f"[Monitor] Retrying in 5 seconds...")
        return None # Will trigger a retry in the main loop
    except Exception as e:
        print(f"[Monitor] An error occurred while trying to start the app: {e}")
        print(f"[Monitor] This could be a permissions issue (e.g., file not found in {app_cwd}).")
        print(f"[Monitor] Retrying in 5 seconds...")
        return None # Will trigger a retry in the main loop

def main():
    """
    Main monitoring loop.
    Starts the app and restarts it if it crashes.
    """
    process = start_flask_app()

    while True:
        try:
            if process is None:
                # App failed to start, wait a bit before retrying
                print("[Monitor] App failed to start. Retrying in 5 seconds...")
                time.sleep(5)
                process = start_flask_app()
                continue

            # wait() will block until the process terminates
            return_code = process.wait()
            
            # If we are here, the process has terminated
            print(f"[Monitor] Flask app process (PID: {process.pid}) terminated unexpectedly with return code: {return_code}.")
            
            # Add a small delay to prevent rapid-fire restarts
            # in case of an immediate, recurring crash loop.
            print("[Monitor] Restarting in 3 seconds...")
            time.sleep(3)
            
            process = start_flask_app() # Restart the app

        except KeyboardInterrupt:
            print("\n[Monitor] Keyboard interrupt received. Stopping monitor and Flask app.")
            if process and process.poll() is None: # Check if process is still running
                print(f"[Monitor] Terminating Flask app (PID: {process.pid})...")
                process.terminate()
                try:
                    # Wait for the process to terminate gracefully
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # If it doesn't terminate, force kill it
                    print("[Monitor] Flask app did not terminate gracefully. Forcing kill.")
                    process.kill()
            print("[Monitor] Exiting.")
            break # Exit the while loop
        
        except Exception as e:
            # Handle other potential errors in the monitor script itself
            print(f"[Monitor] An unexpected error occurred in the monitor: {e}")
            if process and process.poll() is None:
                print("[Monitor] Killing app process due to monitor error.")
                process.kill()
            
            print("[Monitor] Attempting to restart loop in 5 seconds...")
            time.sleep(5)
            process = start_flask_app() # Try to restart

if __name__ == "__main__":
    main()

