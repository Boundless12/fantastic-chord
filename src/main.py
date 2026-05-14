"""酷和弦 - EDM Chord Synthesizer.

Entry point for the Cool Chord desktop synthesizer application.
"""

import logging
import sys

logger = logging.getLogger(__name__)


def main() -> int:
    """Application entry point."""
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger.info("Starting 酷和弦 (Cool Chord)...")

    try:
        from PySide6.QtWidgets import QApplication

        from src.ui.main_window import MainWindow
        from src.ui.theme import apply_dark_theme

        app = QApplication(sys.argv)
        app.setApplicationName("酷和弦")
        app.setOrganizationName("CoolChord")

        apply_dark_theme(app)
        logger.info("Dark theme applied")

        window = MainWindow()
        window.show()
        logger.info("MainWindow displayed")

        return app.exec()
    except ImportError as e:
        logger.error(f"Failed to import required library: {e}")
        logger.error("Ensure virtual environment is activated: source .venv/Scripts/activate")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
