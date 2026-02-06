#!/usr/bin/env python3
"""Unit tests for display functionality."""

import sys
import io
from contextlib import redirect_stdout

from display import (
    submissions_to_dataframe,
    print_table,
    print_csv,
    save_to_csv,
    parse_display_args,
    Colors,
)
from models import Submission


def test_color_coding():
    """Test that color coding works correctly."""
    print("Testing color coding...")

    # Create test submissions with different rating scenarios
    test_subs = [
        Submission(
            title="Paper with sufficient reviews",
            sub_id="TEST001",
            url="https://example.com/paper1",
            ratings=[1, 2, 3, 4],  # 4 ratings - should be green
            confidences=[1, 2, 3, 4],
            final_ratings=[2, 3, 4],  # 3 final ratings - should be green
        ),
        Submission(
            title="Paper with insufficient reviews",
            sub_id="TEST002",
            url="https://example.com/paper2",
            ratings=[1, 2],  # 2 ratings - should be red
            confidences=[1, 2],
            final_ratings=[1, 2],  # 2 final ratings - should be red
        ),
        Submission(
            title="Paper with no reviews",
            sub_id="TEST003",
            url="https://example.com/paper3",
            ratings=[],  # 0 ratings - should be red
            confidences=[],
            final_ratings=[],  # 0 final ratings - should be red
        ),
    ]

    # Test DataFrame creation with URLs
    df = submissions_to_dataframe(test_subs, include_urls=True)

    # Check that color codes are present
    ratings_col = df["Ratings"].tolist()
    final_ratings_col = df["Final_Ratings"].tolist()
    urls_col = df["URL"].tolist()

    # Verify color coding
    assert Colors.GREEN in ratings_col[0], "First submission should have green ratings"
    assert (
        Colors.GREEN in final_ratings_col[0]
    ), "First submission should have green final ratings"
    assert Colors.BLUE in urls_col[0], "First submission should have blue URL"

    assert Colors.RED in ratings_col[1], "Second submission should have red ratings"
    assert (
        Colors.RED in final_ratings_col[1]
    ), "Second submission should have red final ratings"
    assert Colors.BLUE in urls_col[1], "Second submission should have blue URL"

    assert Colors.RED in ratings_col[2], "Third submission should have red ratings"
    assert (
        Colors.RED in final_ratings_col[2]
    ), "Third submission should have red final ratings"
    assert Colors.BLUE in urls_col[2], "Third submission should have blue URL"

    print("✓ Color coding test passed")


def test_csv_output():
    """Test CSV output functionality."""
    print("Testing CSV output...")

    test_subs = [
        Submission(
            title="Test Paper 1",
            sub_id="CSV001",
            url="https://example.com/csv1",
            ratings=[3, 4, 5],
            confidences=[3, 4, 5],
            final_ratings=[4, 5],
        ),
        Submission(
            title="Test Paper 2",
            sub_id="CSV002",
            url="https://example.com/csv2",
            ratings=[1, 2],
            confidences=[1, 2],
            final_ratings=[1],
        ),
    ]

    # Capture CSV output
    f = io.StringIO()
    with redirect_stdout(f):
        print_csv(test_subs, include_urls=True)

    csv_output = f.getvalue()

    # Verify CSV structure
    lines = csv_output.strip().split("\n")
    header_line = lines[0]
    data_lines = lines[2:-1]  # Skip header and separator lines

    # Check header
    assert "CSV OUTPUT" in csv_output, "CSV should have header"

    # Check data lines (skip separator lines)
    data_start_index = 2 if len(lines) > 2 and lines[1].strip() == "" else 1
    data_lines = lines[data_start_index:] if len(lines) > data_start_index else []

    assert (
        len(data_lines) >= 2
    ), f"Should have at least 2 data lines, got {len(data_lines)}: {data_lines}"
    if len(data_lines) >= 1:
        assert "CSV001" in data_lines[0], "First submission should be present"
    if len(data_lines) >= 2:
        assert "CSV002" in data_lines[1], "Second submission should be present"
    assert "https://example.com/csv1" in data_lines[0], "First URL should be present"
    assert "https://example.com/csv2" in data_lines[1], "Second URL should be present"

    # Verify CSV has clean data (no color codes)
    for line in data_lines:
        assert "\033[" not in line, f"CSV line should not have color codes: {line}"

    print("✓ CSV output test passed")


def test_table_output():
    """Test table output functionality."""
    print("Testing table output...")

    test_subs = [
        Submission(
            title="Table Test Paper",
            sub_id="TAB001",
            url="https://example.com/table1",
            ratings=[2, 3, 4],
            confidences=[2, 3, 4],
            final_ratings=[3, 4],
        )
    ]

    # Capture table output
    f = io.StringIO()
    with redirect_stdout(f):
        print_table(test_subs, table_format="grid", include_urls=True)

    table_output = f.getvalue()

    # Verify table structure
    assert "Table Test Paper" in table_output, "Title should be present"
    assert "TAB001" in table_output, "ID should be present"
    assert Colors.BLUE in table_output, "URL should be colored"
    assert Colors.GREEN in table_output, "Ratings should be colored"

    print("✓ Table output test passed")


def test_file_save():
    """Test file saving functionality."""
    print("Testing file save...")

    test_subs = [
        Submission(
            title="Save Test Paper",
            sub_id="SAVE001",
            url="https://example.com/save1",
            ratings=[1, 2, 3],
            confidences=[1, 2, 3],
            final_ratings=[2, 3],
        )
    ]

    # Test file save
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_file:
        save_to_csv(test_subs, tmp_file.name)

        # Read back and verify
        with open(tmp_file.name, "r") as f:
            content = f.read()

        # Clean up
        os.unlink(tmp_file.name)

    # Verify file content
    assert "Save Test Paper" in content, "Title should be in file"
    assert "SAVE001" in content, "ID should be in file"
    assert "https://example.com/save1" in content, "URL should be in file"
    assert "1, 2, 3" in content, "Ratings should be in file"

    print("✓ File save test passed")


def test_argument_parsing():
    """Test command line argument parsing."""
    print("Testing argument parsing...")

    # Test default args
    args = parse_display_args()
    assert args.format == "grid", "Default format should be grid"
    assert args.urls == False, "URLs should be False by default"
    assert args.csv_only == False, "CSV-only should be False by default"

    # Test custom args
    test_args = ["--format", "github", "--urls", "--csv-only"]

    # Mock sys.argv
    original_argv = sys.argv
    sys.argv = ["test_display.py"] + test_args

    try:
        args = parse_display_args()
        assert args.format == "github", "Format should be github"
        assert args.urls == True, "URLs should be True"
        assert args.csv_only == True, "CSV-only should be True"
    finally:
        sys.argv = original_argv

    print("✓ Argument parsing test passed")


def run_all_tests():
    """Run all unit tests."""
    print("Running display functionality tests...\n")

    try:
        test_color_coding()
        test_csv_output()
        test_table_output()
        test_file_save()
        test_argument_parsing()

        print("\n🎉 All tests passed! Display functionality is working correctly.")
        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
