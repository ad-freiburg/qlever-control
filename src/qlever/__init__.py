from pathlib import Path

# Helper function to turn "snake_case" into "CamelCase".
def snake_to_camel(str):
    return "".join([w.capitalize() for w in str.split("_")])

# Each module in `qlever/commands` corresponds to a command. The name
# of the command is the base name of the module file.
package_path = Path(__file__).parent
command_names = [Path(p).stem for p in package_path.glob("commands/*.py")]

# Dynamically load all the command classes.
command_classes = {}
for command_name in command_names:
    module_path = f"qlever.commands.{command_name}"
    class_name = snake_to_camel(command_name) + "Command"
    try:
        module = __import__(module_path, fromlist=[class_name])
    except ImportError as e:
        raise Exception(f"Could not import class {class_name} from module "
                        f"{module_path} for command {command}: {e}")
    command_classes[command_name] = getattr(module, class_name)

print(f"Package path: {package_path}")
print(f"Command names: {command_names}")
print(f"Command classes: {command_classes}")
print()
