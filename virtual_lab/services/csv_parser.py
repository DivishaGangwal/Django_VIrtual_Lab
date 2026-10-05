"""
Pure-Python CSV Parser Service (Zero-Pandas Architecture).
Handles in-memory stream decoding, dialect/delimiter detection,
and tabular dictionary extraction using Python's built-in csv module.
"""

import csv
import io
from typing import Any, Dict, List, Optional

# Cell values treated as "missing" (compared case-insensitively after stripping).
MISSING_TOKENS = {'', 'na', 'n/a', 'null', 'nan', 'none', '-'}


def is_missing(value: Optional[str]) -> bool:
    return value is None or str(value).strip().lower() in MISSING_TOKENS


class CSVParserService:
    """
    Parses raw CSV file streams into structured Python dictionaries
    and computes dataset metadata.
    """

    @staticmethod
    def decode_file_stream(file_obj) -> str:
        """
        Decodes an uploaded file / bytes into text.
        Tries UTF-8 (with and without BOM), then Windows-1252, then Latin-1.
        Latin-1 can decode any byte sequence, so it must be the last resort.
        """
        if hasattr(file_obj, 'read'):
            raw_data = file_obj.read()
        elif isinstance(file_obj, (bytes, bytearray)):
            raw_data = bytes(file_obj)
        elif isinstance(file_obj, str):
            return file_obj
        else:
            raise ValueError("Unsupported file stream type.")

        if isinstance(raw_data, str):
            return raw_data

        for encoding in ('utf-8-sig', 'cp1252', 'latin-1'):
            try:
                return raw_data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw_data.decode('utf-8', errors='replace')  # unreachable in practice

    @staticmethod
    def _detect_delimiter(text: str) -> str:
        # Only sniff complete lines so a half-cut last line doesn't confuse the Sniffer.
        sample = text[:4096]
        if len(text) > 4096 and '\n' in sample:
            sample = sample[:sample.rfind('\n')]
        try:
            return csv.Sniffer().sniff(sample, delimiters=',;\t|').delimiter
        except csv.Error:
            return ','

    @staticmethod
    def _clean_headers(raw_headers: List[str]) -> List[str]:
        """
        Strips whitespace, names blank headers 'Column_N' and de-duplicates
        repeated names ('id', 'id' -> 'id', 'id_2') so no column is lost.
        """
        headers: List[str] = []
        seen: Dict[str, int] = {}
        for idx, raw in enumerate(raw_headers, start=1):
            name = (raw or '').strip() or f'Column_{idx}'
            base = name
            if base in seen:
                seen[base] += 1
                name = f'{base}_{seen[base]}'
                while name in seen:
                    seen[base] += 1
                    name = f'{base}_{seen[base]}'
            seen.setdefault(name, 1)
            headers.append(name)
        return headers

    @classmethod
    def parse_csv_content(
        cls,
        file_content: str,
        max_preview_rows: int = 5,
        max_rows: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Parses CSV text using csv.reader (positional), mapping each cell to the
        cleaned header. Returns a dict with:
            status, headers, rows, row_count, col_count, preview_rows,
            delimiter, missing_values_count, ragged_rows_count, truncated
        """
        if not file_content or not file_content.strip():
            return {'status': 'error', 'message': 'The CSV content is empty.'}

        delimiter = cls._detect_delimiter(file_content)
        stream = io.StringIO(file_content.strip('\r\n'))

        try:
            reader = csv.reader(stream, delimiter=delimiter)
            raw_headers = next(reader, None)
            if not raw_headers or not any(h.strip() for h in raw_headers):
                return {'status': 'error', 'message': 'Could not detect column headers in the CSV file.'}

            headers = cls._clean_headers(raw_headers)
            col_count = len(headers)

            rows: List[Dict[str, str]] = []
            missing_count = 0
            ragged_count = 0
            truncated = False

            for cells in reader:
                if not any(c.strip() for c in cells):
                    continue  # skip blank lines
                if max_rows is not None and len(rows) >= max_rows:
                    truncated = True
                    break
                if len(cells) != col_count:
                    ragged_count += 1
                    cells = (cells + [''] * col_count)[:col_count]

                cleaned_row = {}
                for col, val in zip(headers, cells):
                    val = val.strip()
                    if is_missing(val):
                        missing_count += 1
                    cleaned_row[col] = val
                rows.append(cleaned_row)

            if not rows:
                return {'status': 'error', 'message': 'The CSV file contains column headers but zero data rows.'}

            return {
                'status': 'success',
                'headers': headers,
                'rows': rows,
                'row_count': len(rows),
                'col_count': col_count,
                'preview_rows': rows[:max_preview_rows],
                'delimiter': delimiter,
                'missing_values_count': missing_count,
                'ragged_rows_count': ragged_count,
                'truncated': truncated,
            }

        except csv.Error as e:
            return {'status': 'error', 'message': f'CSV parsing error: {e}'}
