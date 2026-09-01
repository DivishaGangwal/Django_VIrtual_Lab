"""
Pure-Python CSV Parser Service (Zero-Pandas Architecture).
Handles in-memory stream decoding, dialect/delimiter detection,
and tabular dictionary extraction using Python's built-in csv module.
"""

import csv
import io
from typing import Dict, List, Any, Tuple, Optional


class CSVParserService:
    """
    Service responsible for parsing raw CSV file streams into structured
    Python dictionaries and computing dataset metadata.
    """

    @staticmethod
    def decode_file_stream(file_obj) -> str:
        """
        Decodes an in-memory or on-disk file stream into a clean UTF-8 string.
        Gracefully handles UTF-8 with BOM, Latin-1, and Windows-1252.
        """
        if hasattr(file_obj, 'read'):
            raw_data = file_obj.read()
        elif isinstance(file_obj, (bytes, bytearray)):
            raw_data = file_obj
        elif isinstance(file_obj, str):
            return file_obj
        else:
            raise ValueError("Unsupported file stream type.")

        # Attempt decoding with UTF-8 with BOM first, then UTF-8, then Latin-1
        for encoding in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
            try:
                return raw_data.decode(encoding)
            except (UnicodeDecodeError, AttributeError):
                continue

        # Fallback with replacement of un-decodable characters
        return raw_data.decode('utf-8', errors='replace')

    @classmethod
    def parse_csv_content(cls, file_content: str, max_preview_rows: int = 5) -> Dict[str, Any]:
        """
        Parses raw CSV string content using Python's standard csv module.
        
        Returns:
            dict containing:
                - 'status': 'success' | 'error'
                - 'headers': list of sanitized column name strings
                - 'rows': list of row dicts
                - 'row_count': total number of data rows
                - 'col_count': total number of columns
                - 'preview_rows': first N rows
                - 'delimiter': detected delimiter char (e.g. ',', ';', '\t')
                - 'missing_values_count': count of empty cells
        """
        if not file_content or not file_content.strip():
            return {
                'status': 'error',
                'message': 'The CSV content is empty.'
            }

        # Step 1: Detect delimiter using csv.Sniffer
        sample_size = min(len(file_content), 4096)
        sample_chunk = file_content[:sample_size]
        delimiter = ','

        try:
            sniffer = csv.Sniffer()
            # Sniff dialect with preferred delimiters
            dialect = sniffer.sniff(sample_chunk, delimiters=',;\t|')
            delimiter = dialect.delimiter
        except csv.Error:
            # Default to standard comma if sniffer cannot determine dialect
            delimiter = ','

        # Step 2: In-Memory Stream Processing with io.StringIO
        text_stream = io.StringIO(file_content.strip())

        try:
            # Step 3: DictReader Tabular Extraction
            reader = csv.DictReader(text_stream, delimiter=delimiter)
            
            # Clean and sanitize headers (remove whitespace, skip empty keys)
            if not reader.fieldnames:
                return {
                    'status': 'error',
                    'message': 'Could not detect column headers in the CSV file.'
                }

            raw_headers = [h for h in reader.fieldnames if h is not None]
            headers = [h.strip() for h in raw_headers if h.strip()]

            if not headers:
                return {
                    'status': 'error',
                    'message': 'No valid column headers found in the CSV file.'
                }

            rows: List[Dict[str, str]] = []
            missing_count = 0

            for row_idx, row in enumerate(reader, start=1):
                # Skip completely blank lines
                if not any(row.values()):
                    continue

                cleaned_row = {}
                for col in headers:
                    val = row.get(col, '')
                    if val is None:
                        val = ''
                    else:
                        val = str(val).strip()
                    
                    if val == '' or val.lower() in ('na', 'null', 'nan', 'none', '-'):
                        missing_count += 1
                    
                    cleaned_row[col] = val

                rows.append(cleaned_row)

            row_count = len(rows)
            col_count = len(headers)

            if row_count == 0:
                return {
                    'status': 'error',
                    'message': 'The CSV file contains column headers but zero data rows.'
                }

            return {
                'status': 'success',
                'headers': headers,
                'rows': rows,
                'row_count': row_count,
                'col_count': col_count,
                'preview_rows': rows[:max_preview_rows],
                'delimiter': delimiter,
                'missing_values_count': missing_count,
            }

        except csv.Error as e:
            return {
                'status': 'error',
                'message': f'CSV Parsing Error: {str(e)}'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Unexpected processing error: {str(e)}'
            }
