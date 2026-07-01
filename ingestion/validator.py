import zipfile
from pathlib import Path


class EpubValidator:
    def validate(self, epub_path: Path) -> None:
        """
        Validates that the file exists, is a zip archive, and contains EPUB metadata.
        Raises ValueError with failure_stage if invalid.
        """
        if not epub_path.exists():
            raise ValueError("epub_validation: File does not exist")

        if epub_path.stat().st_size == 0:
            raise ValueError("epub_validation: File is empty")

        if not zipfile.is_zipfile(epub_path):
            raise ValueError("epub_validation: File is not a valid ZIP archive")

        try:
            with zipfile.ZipFile(epub_path, "r") as z:
                files = z.namelist()
                if "META-INF/container.xml" not in files:
                    raise ValueError("epub_validation: META-INF/container.xml missing")
        except zipfile.BadZipFile:
            raise ValueError("epub_validation: Corrupted ZIP archive")
