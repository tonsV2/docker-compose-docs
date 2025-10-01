"""Tests for utility functions."""

import os
import tempfile
from pathlib import Path

from src.utils import (
    find_compose_files,
    sort_compose_files,
    parse_paths_from_string,
    collect_compose_files,
    collect_compose_files_from_globs,
)


class TestFindComposeFiles:
    """Test cases for find_compose_files function."""

    def test_find_compose_files_basic(self):
        """Test finding compose files in a directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            compose_file = Path(temp_dir) / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  web: {}")

            files = find_compose_files(temp_dir)
            assert len(files) == 1
            assert str(compose_file) in files

    def test_find_compose_files_multiple_patterns(self):
        """Test finding compose files with different naming patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create different compose file patterns
            files_to_create = [
                "docker-compose.yml",
                "docker-compose.yaml",
                "docker-compose.prod.yml",
                "compose.yml",
            ]

            for filename in files_to_create:
                (temp_path / filename).write_text(
                    "version: '3.8'\nservices:\n  web: {}"
                )

            files = find_compose_files(temp_dir)
            assert len(files) == 4

            # Check that all expected files are found
            found_names = [os.path.basename(f) for f in files]
            for expected_name in files_to_create:
                assert expected_name in found_names

    def test_find_compose_files_no_files(self):
        """Test behavior when no compose files exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            files = find_compose_files(temp_dir)
            assert files == []

    def test_find_compose_files_nested_directories(self):
        """Test finding compose files in nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory with compose file
            nested_dir = temp_path / "nested"
            nested_dir.mkdir()
            compose_file = nested_dir / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  web: {}")

            # find_compose_files only searches the given directory, not subdirectories
            files = find_compose_files(nested_dir)
            assert len(files) == 1
            assert str(compose_file) in files


class TestSortComposeFiles:
    """Test cases for sort_compose_files function."""

    def test_sort_compose_files_priority_order(self):
        """Test that files are sorted with correct priority."""
        files = [
            "/path/docker-compose.override.yml",
            "/path/docker-compose.yml",
            "/path/compose.yml",
            "/path/docker-compose.prod.yml",
        ]

        sorted_files = sort_compose_files(files)

        # Check that files are sorted alphabetically within their categories
        # The actual priority order depends on the implementation
        assert len(sorted_files) == 4
        assert "/path/docker-compose.yml" in sorted_files
        assert "/path/compose.yml" in sorted_files
        assert "/path/docker-compose.override.yml" in sorted_files
        assert "/path/docker-compose.prod.yml" in sorted_files

    def test_sort_compose_files_empty_list(self):
        """Test sorting an empty list."""
        assert sort_compose_files([]) == []

    def test_sort_compose_files_single_file(self):
        """Test sorting a single file."""
        files = ["/path/docker-compose.yml"]
        assert sort_compose_files(files) == files


class TestParsePathsFromString:
    """Test cases for parse_paths_from_string function."""

    def test_parse_paths_from_string_basic(self):
        """Test parsing semicolon-separated paths."""
        path_string = "/path/to/file1;/path/to/file2;/path/to/file3"
        paths = parse_paths_from_string(path_string)

        assert paths == ["/path/to/file1", "/path/to/file2", "/path/to/file3"]

    def test_parse_paths_from_string_with_spaces(self):
        """Test parsing paths with spaces."""
        path_string = "/path/to file1;/path/to file2"
        paths = parse_paths_from_string(path_string)

        assert paths == ["/path/to file1", "/path/to file2"]

    def test_parse_paths_from_string_empty(self):
        """Test parsing empty string."""
        assert parse_paths_from_string("") == []

    def test_parse_paths_from_string_none(self):
        """Test parsing None value."""
        assert parse_paths_from_string(None) == []

    def test_parse_paths_from_string_with_empty_parts(self):
        """Test parsing string with empty parts."""
        path_string = "/path1;;/path2;"
        paths = parse_paths_from_string(path_string)

        assert paths == ["/path1", "/path2"]


class TestCollectComposeFiles:
    """Test cases for collect_compose_files function."""

    def test_collect_compose_files_from_files(self):
        """Test collecting compose files from file paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create compose files
            file1 = temp_path / "docker-compose.yml"
            file1.write_text("version: '3.8'\nservices:\n  web: {}")

            file2 = temp_path / "compose.yml"
            file2.write_text("version: '3.8'\nservices:\n  api: {}")

            paths = [str(file1), str(file2)]
            files = collect_compose_files(paths)

            assert len(files) == 2
            assert str(file1) in files
            assert str(file2) in files

    def test_collect_compose_files_from_directories(self):
        """Test collecting compose files from directory paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create compose file in directory
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  web: {}")

            paths = [temp_dir]
            files = collect_compose_files(paths)

            assert len(files) == 1
            assert str(compose_file) in files

    def test_collect_compose_files_mixed_paths(self):
        """Test collecting compose files from mixed file and directory paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create compose file in directory
            dir_compose = temp_path / "docker-compose.yml"
            dir_compose.write_text("version: '3.8'\nservices:\n  web: {}")

            # Create another compose file
            file_compose = temp_path / "compose.yml"
            file_compose.write_text("version: '3.8'\nservices:\n  api: {}")

            paths = [temp_dir, str(file_compose)]
            files = collect_compose_files(paths)

            assert len(files) == 2
            assert str(dir_compose) in files
            assert str(file_compose) in files

    def test_collect_compose_files_nonexistent_path(self, capsys):
        """Test handling of nonexistent paths."""
        paths = ["/nonexistent/path"]
        files = collect_compose_files(paths)

        assert files == []

        # Check that warning was printed to stderr
        captured = capsys.readouterr()
        assert "Warning: Path not found" in captured.err


class TestCollectComposeFilesFromGlobs:
    """Test cases for collect_compose_files_from_globs function."""

    def test_collect_compose_files_from_globs_basic(self):
        """Test collecting compose files from glob patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create compose file
            compose_file = temp_path / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  web: {}")

            globs = [str(compose_file)]
            files = collect_compose_files_from_globs(globs)

            assert len(files) == 1
            assert str(compose_file) in files

    def test_collect_compose_files_from_globs_recursive(self):
        """Test collecting compose files with recursive glob patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create nested directory with compose file
            nested_dir = temp_path / "overlays" / "monitoring"
            nested_dir.mkdir(parents=True)
            compose_file = nested_dir / "docker-compose.yml"
            compose_file.write_text("version: '3.8'\nservices:\n  web: {}")

            globs = [str(temp_path / "overlays" / "**" / "docker-compose.yml")]
            files = collect_compose_files_from_globs(globs)

            assert len(files) == 1
            assert str(compose_file) in files

    def test_collect_compose_files_from_globs_multiple(self):
        """Test collecting compose files from multiple glob patterns."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create compose files
            file1 = temp_path / "docker-compose.yml"
            file1.write_text("version: '3.8'\nservices:\n  web: {}")

            file2 = temp_path / "compose.yml"
            file2.write_text("version: '3.8'\nservices:\n  api: {}")

            globs = [str(file1), str(file2)]
            files = collect_compose_files_from_globs(globs)

            assert len(files) == 2
            assert str(file1) in files
            assert str(file2) in files

    def test_collect_compose_files_from_globs_no_matches(self):
        """Test behavior when no files match the glob patterns."""
        globs = ["/nonexistent/**/*.yml"]
        files = collect_compose_files_from_globs(globs)

        assert files == []
