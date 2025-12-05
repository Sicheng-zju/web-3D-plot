import gmsh
import sys
import os

def convert(input_path, output_path):
    try:
        gmsh.initialize()
        gmsh.clear()
        gmsh.merge(input_path)
        
        # Improve mesh quality for visualization
        # Enable curvature-based meshing (more elements on curves)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 30) 
        # Set a global mesh size factor (smaller = finer, default is 1.0)
        gmsh.option.setNumber("Mesh.MeshSizeFactor", 0.5)
        # Optimize the mesh for 3D display
        gmsh.option.setNumber("Mesh.Algorithm", 6) # Frontal-Delaunay for 2D
        
        gmsh.model.mesh.generate(2)
        gmsh.write(output_path)
        gmsh.finalize()
        return True
    except Exception as e:
        print(f"Conversion error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_script.py <input_path> <output_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if convert(input_path, output_path):
        sys.exit(0)
    else:
        sys.exit(1)
