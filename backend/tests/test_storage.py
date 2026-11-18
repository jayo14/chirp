import os
import pytest
from backend.app.integrations.storage.local import LocalStorageProvider


@pytest.mark.asyncio
async def test_save_normal_file(tmp_path):
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    content = b"sample assignment text"
    url, path = await storage.save_file(content, "assignment1.pdf", "application/pdf")

    assert os.path.exists(path)
    assert path.startswith(str(tmp_path))
    assert url.startswith("file://")
    read_back = await storage.read_file(path)
    assert read_back == content


@pytest.mark.asyncio
async def test_prevent_directory_traversal_on_save(tmp_path):
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    content = b"malicious content"

    # Filename trying to escape up to parent directory
    url, path = await storage.save_file(content, "../../../../etc/passwd", "text/plain")

    # Path must remain strictly within tmp_path
    assert os.path.exists(path)
    assert os.path.commonpath([str(tmp_path), os.path.abspath(path)]) == str(tmp_path)
    # The file name must have been sanitized
    assert "passwd" in os.path.basename(path)
    assert not os.path.exists("/etc/passwd.test")


@pytest.mark.asyncio
async def test_prevent_directory_traversal_on_read(tmp_path):
    storage = LocalStorageProvider(base_dir=str(tmp_path))

    with pytest.raises(ValueError, match="Path traversal attempt detected"):
        await storage.read_file("../../../etc/shadow")


@pytest.mark.asyncio
async def test_sanitize_empty_or_dangerous_names(tmp_path):
    storage = LocalStorageProvider(base_dir=str(tmp_path))
    url, path = await storage.save_file(b"test", "....", "text/plain")

    assert os.path.exists(path)
    assert "attachment.bin" in os.path.basename(path)
