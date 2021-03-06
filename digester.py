import argparse
from collections import OrderedDict
from csv import DictReader
from functools import reduce
import re
import sys
from typing import Dict, List, Mapping, Union
import unittest

SAMPLE_RESULTS_PATH = "sample_results.csv"
DEFAULT_SEGMENTS = ["Swim", "T1", "Bike", "T2", "Run"]
TOTAL_KEY = "Gun"


def load_and_format_results(
            path: str,
            segments: List[str],
            total_key: str
        ) -> List[Dict[str, Union[int, str]]]:
    unformatted_results = load_results(path)
    parsed_results = [get_segment_times(result, segments, total_key) for result in unformatted_results]
    patched_results = estimate_missing_results_values(parsed_results, segments, total_key)
    return patched_results


def load_results(path: str=SAMPLE_RESULTS_PATH) -> List[Dict[str, str]]:
    with open(path, "r") as csvfile:
        reader = DictReader(csvfile)
        rows = [dict(row) for row in reader]
    return rows


def get_segment_times(
            row: Dict[str, str],
            segments: List[str],
            total_key: str
        ) -> Dict[str, Union[int, str]]:
    new_row = {}
    for key, value in row.items():
        new_value: Union[int, str]
        if key in segments or key == total_key:
            new_value = parse_time(value)
        else:
            new_value = value
        new_row[key] = new_value
    return new_row


def parse_time(time_string: str) -> int:
    match = re.match(r"(\d+):(\d+):(\d+)", time_string)
    if match is None:
        raise TypeError(f"{time_string} is not in the format XX:XX:XX")
    tokens = [int(g) for g in match.groups()]
    return reduce(lambda x, y: 60*x + y, tokens)


def estimate_missing_results_values(
            results: List[Dict[str, Union[int, str]]],
            segments: List[str],
            total_key: str
        ) -> List[Dict[str, Union[int, str]]]:
    segment_proportions = calculate_proportions(results, segments, total_key)
    return [
        estimate_missing_row_values(row, segment_proportions, segments, total_key)
        for row in results
    ]


def calculate_proportions(
            results: List[Dict[str, Union[int, str]]],
            segments: List[str],
            total_key: str
        ) -> Dict[str, float]:
    total_time = sum(int(row[total_key]) for row in results)
    segment_proportions = {
        segment: sum(int(row[segment]) for row in results) / total_time
        for segment in segments
    }
    return segment_proportions



def estimate_missing_row_values(
            row: Dict[str, Union[int, str]],
            proportions: Dict[str, float],
            segments: List[str],
            total_key: str
        ) -> Dict[str, Union[int, str]]:
    missing_segments = [segment for segment in segments if row[segment] == 0]
    counted_time = sum(int(row[segment]) for segment in segments)
    uncounted_time = int(row[total_key]) - counted_time
    total_proportion_uncounted = sum(proportions[segment] for segment in missing_segments)
    new_row = {}
    for key, value in row.items():
        if key not in missing_segments:
            new_row[key] = value
        else:
            new_value = (round(uncounted_time * proportions[key] / total_proportion_uncounted))
            new_row[key] = new_value
    return new_row


class Tests(unittest.TestCase):

    def test_parse_time(self: unittest.TestCase) -> None:
        time_string = "01:02:03"
        expected_time = 1*60**2 + 2*60 + 3
        parsed_time = parse_time(time_string)
        self.assertEqual(parsed_time, expected_time)

    def test_estimation(self: unittest.TestCase) -> None:
        row: Dict[str, Union[int, str]] = {"Swim": 0, "T1": 0, "Bike": 2300, "T2": 60, "Run": 1200, "Gun": 4160}
        # Uncounted time is 600 seconds
        proportions = {"Swim": 0.2, "T1": 0.03, "Bike": 0.45, "T2": 0.02, "Run": 0.3}
        expected_swim = 522
        expected_t1 = 78
        estimates = estimate_missing_row_values(row, proportions, DEFAULT_SEGMENTS, TOTAL_KEY)
        self.assertEqual(estimates["Swim"], expected_swim)
        self.assertEqual(estimates["T1"], expected_t1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filepath", help="location of the csv with the results")
    parser.add_argument("--segments", help="comma-separated string of segment headers")
    parser.add_argument("--totalheader", help="header for the total time")
    args = parser.parse_args()
    filepath = args.filepath
    if args.segments:
        segments = [s.strip() for s in args.segments.split(",")]
    else:
        segments = DEFAULT_SEGMENTS
    if args.totalheader:
        total_key = args.totalheader
    else:
        total_key = TOTAL_KEY
    results = load_and_format_results(filepath, segments, total_key)
