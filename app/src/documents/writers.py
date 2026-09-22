from pathlib import Path
from typing import Any, Optional

from src.utils import Log


class ImageWriter:
    """Writer for image files extracted from PDFs via pypdfium2."""

    def __init__(self, base_output_dir: Path):
        self.base_output_dir: Path = Path(base_output_dir)

    def ensure_directory(self, directory_path: Path) -> bool:
        try:
            directory_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            Log.error(
                message=f"Error creating directory {directory_path}: {e}", source=self)
            return False

    def write(self, pdf_image: Any, output_path_prefix: Path) -> Optional[Path]:
        """Save a pypdfium2 PdfImage to disk. Return the final on-disk Path, or None on error.

        output_path_prefix -- path without extension; pypdfium2 appends the correct one
        """
        try:
            self.ensure_directory(output_path_prefix.parent)
            final_path = pdf_image.extract(str(output_path_prefix))
            return Path(final_path) if final_path else None
        except Exception as e:
            Log.warning(
                message=f"Image skipped ({output_path_prefix.name}): {e}",
                source=self,
            )
            return None
