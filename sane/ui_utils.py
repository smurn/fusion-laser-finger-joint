import adsk.core
from .event_utils import register_event_handler

app = adsk.core.Application.get()
ui = app.userInterface


def print_toolbar_structure():
    for workspace in ui.workspaces:
        print(f"WORKSPACE {workspace.name!r} ({workspace.id!r})")
        try:
            for panel in workspace.toolbarPanels:
                print(f"  PANEL {panel.name!r} ({panel.id!r})")
        except RuntimeError:
            pass