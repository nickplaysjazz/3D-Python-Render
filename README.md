## 3D Python Render
A simple 3D rendering tool built in PyGame using PyOpenGL for graphics.


### Installation
Create a virtual environment with pip: `python -m venv render` will create the venv called "render" as a subdirectory.

Activate the virtual environment with `source render/Scripts/activate` or `source render/bin/activate`, depending on your OS. (You can deactivate the virtual environment with `deactivate`.)

If this is your first time installing, install required packages with `pip install -r requirements.txt`. 

Run the program with `python main.py`.


### Notes
This project is a work in progress.

### TODO
- Adding objects loaded from `/assets/` folder
- Fix CCW definitions of triangular cube faces, disabled CULL_FACE in the meantime
- Mobile lighting
- Specular lighting?
- Textures/materials
