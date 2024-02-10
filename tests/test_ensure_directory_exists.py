import os
import pytest
import tempfile
from pan_os_upgrade.upgrade import ensure_directory_exists


def test_ensure_directory_exists_creates_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Construct a nested directory path inside the temporary directory
        nested_dir_path = os.path.join(temp_dir, "nested", "subdir")
        file_path = os.path.join(nested_dir_path, "testfile.txt")

        # Ensure the nested directory does not exist yet
        assert not os.path.exists(nested_dir_path)

        # Call the function to ensure the directory exists
        ensure_directory_exists(file_path)

        # Verify the directory was created
        assert os.path.exists(nested_dir_path), "The directory should have been created"


def test_ensure_directory_exists_with_existing_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Use the temporary directory itself as the target, which already exists
        file_path = os.path.join(temp_dir, "testfile.txt")

        # The directory already exists, so the function should not raise any error
        ensure_directory_exists(file_path)

        # Just to be sure, check the directory still exists
        assert os.path.exists(temp_dir), "The directory should still exist"


def test_ensure_directory_exists_raises_oserror_with_invalid_path():
    # Using a path that is likely to be invalid or unwritable on most systems
    invalid_path = "/this/path/should/not/exist/testfile.txt"

    # Expecting an OSError due to permission error or non-existent path
    with pytest.raises(OSError):
        ensure_directory_exists(invalid_path)
