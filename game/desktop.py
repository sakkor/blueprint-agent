"""Space Fractions desktop entry point (EMAIL-DESKTOP).

Constructs a native tkinter.Tk window directly and runs its mainloop.
Run: python desktop.py
"""

import tkinter as tk

from spacefractions.ui import build_controller, SpaceFractionsApp


def main() -> None:
    root = tk.Tk()  # native Tk window
    controller = build_controller()
    SpaceFractionsApp(root, controller)
    root.mainloop()


if __name__ == "__main__":
    main()
