import sys
import os

# Ensure the project root is on the path when run directly
sys.path.insert(0, os.path.dirname(__file__))

from app.gui.app_window import AppWindow


def main():
    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
