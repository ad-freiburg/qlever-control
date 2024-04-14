from __future__ import annotations

import sys
from pathlib import Path


# Helper function to turn "snake_case" into "CamelCase".
def snake_to_camel(str):
    # Split by _ and - and capitalize each word.
    return "".join([w.capitalize() for w in str.replace("-", "_").split("_")])


# Each module in `qlever/commands` corresponds to a command. The name
# of the command is the base name of the module file.
package_path = Path(__file__).parent
command_names = [Path(p).stem for p in package_path.glob("commands/*.py")
                 if p.name != "__init__.py"]

# Dynamically load all the command classes and create an object for each.
command_objects = {}
for command_name in command_names:
    module_path = f"qlever.commands.{command_name}"
    class_name = snake_to_camel(command_name) + "Command"
    try:
        module = __import__(module_path, fromlist=[class_name])
    except ImportError as e:
        raise Exception(f"Could not import class {class_name} from module "
                        f"{module_path} for command {command_name}: {e}")
    # Create an object of the class and store it in the dictionary. For the
    # commands, take - instead of _.
    command_class = getattr(module, class_name)
    command_objects[command_name.replace("_", "-")] = command_class()

# Get the name of the script (without the path and without the extension).
script_name = Path(sys.argv[0]).stem
