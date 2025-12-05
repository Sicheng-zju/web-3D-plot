import subprocess
import sys
import os

def convert_cad_to_stl(input_path, output_path):
    """
    Convert CAD file (STP, IGS) to STL using a separate process to avoid threading issues.
    """
    try:
        # Get the python executable path
        python_exe = sys.executable
        script_path = os.path.join(os.path.dirname(__file__), 'convert_script.py')
        
        result = subprocess.run(
            [python_exe, script_path, input_path, output_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Conversion failed: {result.stderr}", file=sys.stderr)
            return False
            
        return True
    except Exception as e:
        print(f"Error running conversion script: {e}", file=sys.stderr)
        return False
