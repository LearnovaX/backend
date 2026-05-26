SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".xml",
    ".html",
    ".css",
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".sql",
    ".sh",
}
SUPPORTED_DOCX_EXTENSIONS = {".docx"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_ARCHIVE_EXTENSIONS = {".zip"}
UNSUPPORTED_NESTED_ARCHIVE_EXTENSIONS = SUPPORTED_ARCHIVE_EXTENSIONS | {".rar", ".7z", ".tar", ".gz", ".bz2"}

PLAGIARISM_SIMILARITY_THRESHOLD = 0.80
MIN_TEXT_LENGTH_FOR_COMPARISON = 80

MAX_TEXT_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_DOC_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_FILE_SIZE_BYTES = 8 * 1024 * 1024
MAX_OCR_PIXELS = 12_000_000

MAX_ARCHIVE_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_FILE_COUNT = 1000
MAX_ARCHIVE_MEMBER_BYTES = 25 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 500_000
