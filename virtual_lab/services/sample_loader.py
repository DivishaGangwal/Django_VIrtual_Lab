"""
Helper service to locate and load pre-packaged educational CSV datasets.
"""

from pathlib import Path
from typing import Dict, Any, List
from django.conf import settings
from .csv_parser import CSVParserService

DATA_SAMPLES_DIR = settings.BASE_DIR / 'virtual_lab' / 'data_samples'

AVAILABLE_SAMPLES = {
    'student_marks': {
        'id': 'student_marks',
        'name': 'Student Examination Performance',
        'description': 'Student marks, attendance percentages, and grade distributions (Categorical + Numeric).',
        'filename': 'student_marks.csv'
    },
    'monthly_weather': {
        'id': 'monthly_weather',
        'name': 'Monthly Climate & Weather Telemetry',
        'description': 'Monthly average temperatures, precipitation in mm, humidity, and wind speed trends.',
        'filename': 'monthly_weather.csv'
    },
    'server_metrics': {
        'id': 'server_metrics',
        'name': 'Server Infrastructure Telemetry',
        'description': 'Real-time CPU, RAM, Disk I/O, and network latency metrics across server nodes.',
        'filename': 'server_metrics.csv'
    }
}


class SampleLoaderService:
    """
    Manages discovery and parsing of built-in sample datasets.
    """

    @classmethod
    def get_sample_list(cls) -> List[Dict[str, str]]:
        return list(AVAILABLE_SAMPLES.values())

    @classmethod
    def load_sample_dataset(cls, sample_id: str) -> Dict[str, Any]:
        """
        Loads and parses a sample CSV dataset by ID using the pure Python parser.
        """
        sample_meta = AVAILABLE_SAMPLES.get(sample_id)
        if not sample_meta:
            # Fallback to student_marks if invalid ID
            sample_id = 'student_marks'
            sample_meta = AVAILABLE_SAMPLES['student_marks']

        file_path = DATA_SAMPLES_DIR / sample_meta['filename']
        if not file_path.exists():
            return {
                'status': 'error',
                'message': f"Sample file '{sample_meta['filename']}' not found on server."
            }

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            result = CSVParserService.parse_csv_content(content)
            if result.get('status') == 'success':
                result['sample_info'] = sample_meta
            return result
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Failed to load sample dataset: {str(e)}"
            }
