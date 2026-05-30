
class Node:
    """The Data Container used by the GUI to hold a Logic Object."""
    def __init__(self, name, icon_path, logic_object):
        self.name = name
        self.icon_image = icon_path
        self.object_field = logic_object