"""
Helper service to locate and load pre-packaged educational CSV datasets.
"""

from pathlib import Path
from typing import Any, Dict, List

from .csv_parser import CSVParserService

DATA_SAMPLES_DIR = Path(__file__).resolve().parent.parent / 'data_samples'

AVAILABLE_SAMPLES = {
    'student_marks': {
        'id': 'student_marks',
        'name': 'Student Examination Performance',
        'description': 'Student marks, attendance percentages, and grade distributions (Categorical + Numeric).',
        'filename': 'student_marks.csv',
    },
    'monthly_weather': {
        'id': 'monthly_weather',
        'name': 'Monthly Climate & Weather Telemetry',
        'description': 'Monthly average temperatures, precipitation in mm, humidity, and wind speed trends.',
        'filename': 'monthly_weather.csv',
    },
    'server_metrics': {
        'id': 'server_metrics',
        'name': 'Server Infrastructure Telemetry',
        'description': 'CPU, RAM, Disk I/O, and network latency metrics across server nodes.',
        'filename': 'server_metrics.csv',
    },
    'lab_sensor_log': {
        'id': 'lab_sensor_log',
        'name': 'Lab Sensor Log (with missing values)',
        'description': 'Dated temperature/voltage readings with deliberate gaps and a semicolon delimiter, for practising data cleaning.',
        'filename': 'lab_sensor_log.csv',
    },
}


class SampleLoaderService:
    """Manages discovery and parsing of built-in sample datasets."""

    @classmethod
    def get_sample_list(cls) -> List[Dict[str, str]]:
        return list(AVAILABLE_SAMPLES.values())

    @classmethod
    def load_sample_dataset(cls, sample_id: str, max_rows=None) -> Dict[str, Any]:
        sample_meta = AVAILABLE_SAMPLES.get(sample_id)
        if not sample_meta:
            return {'status': 'error', 'message': f"Unknown sample dataset '{sample_id}'."}

        file_path = DATA_SAMPLES_DIR / sample_meta['filename']
        if not file_path.exists():
            return {'status': 'error', 'message': f"Sample file '{sample_meta['filename']}' not found on server."}

        content = CSVParserService.decode_file_stream(file_path.read_bytes())
        result = CSVParserService.parse_csv_content(content, max_rows=max_rows)
        if result.get('status') == 'success':
            result['sample_info'] = sample_meta
        return result
