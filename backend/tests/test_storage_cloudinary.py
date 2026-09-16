"""Cloudinary resume storage: the raw-resource public_id must embed the extension consistently
between upload and download (mismatched public_id/format was a real live 404 bug), and
re-uploading with a different file type must clean up the old resource."""
import pytest

from app.services import storage


@pytest.fixture
def fake_cloudinary(monkeypatch):
    monkeypatch.setattr(storage.settings, "CLOUDINARY_URL", "cloudinary://key:secret@cloud")

    import cloudinary.uploader
    import cloudinary.utils

    uploaded: dict[str, bytes] = {}
    destroyed: list[str] = []

    def fake_upload(file, **options):
        data = file.read() if hasattr(file, "read") else file
        uploaded[options["public_id"]] = data
        assert options["resource_type"] == "raw"
        assert options["type"] == "authenticated"
        return {"public_id": options["public_id"]}

    def fake_destroy(public_id, **options):
        destroyed.append(public_id)
        uploaded.pop(public_id, None)

    def fake_private_download_url(public_id, fmt, **options):
        assert fmt == "", "format must be empty - it's already embedded in public_id"
        return f"https://fake.cloudinary.test/{public_id}"

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)
    monkeypatch.setattr(cloudinary.uploader, "destroy", fake_destroy)
    monkeypatch.setattr(cloudinary.utils, "private_download_url", fake_private_download_url)
    return uploaded, destroyed


async def test_upload_embeds_extension_in_public_id(fake_cloudinary):
    uploaded, _ = fake_cloudinary
    path = await storage.save_resume(123, b"pdf bytes", "application/pdf", "resume.pdf")

    assert path == "cloudinary:resumes/123/resume.pdf"
    assert uploaded["resumes/123/resume.pdf"] == b"pdf bytes"


async def test_download_url_uses_same_public_id_as_upload(fake_cloudinary):
    path = await storage.save_resume(123, b"pdf bytes", "application/pdf", "resume.pdf")
    url = await storage.get_resume_url(path)

    assert url == "https://fake.cloudinary.test/resumes/123/resume.pdf"


async def test_reupload_with_different_extension_deletes_old_resource(fake_cloudinary):
    uploaded, destroyed = fake_cloudinary
    first_path = await storage.save_resume(123, b"pdf bytes", "application/pdf", "resume.pdf")

    second_path = await storage.save_resume(
        123, b"docx bytes",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "resume.docx",
        previous_resume_path=first_path,
    )

    assert second_path == "cloudinary:resumes/123/resume.docx"
    assert destroyed == ["resumes/123/resume.pdf"]
    assert "resumes/123/resume.pdf" not in uploaded
    assert uploaded["resumes/123/resume.docx"] == b"docx bytes"


async def test_reupload_with_same_extension_does_not_call_destroy(fake_cloudinary):
    _, destroyed = fake_cloudinary
    first_path = await storage.save_resume(123, b"v1", "application/pdf", "resume.pdf")
    await storage.save_resume(123, b"v2", "application/pdf", "resume.pdf", previous_resume_path=first_path)

    assert destroyed == []  # overwrite=True on the same public_id handles this, no destroy needed


async def test_local_fallback_when_cloudinary_not_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(storage.settings, "CLOUDINARY_URL", "")
    monkeypatch.setattr(storage.settings, "UPLOAD_DIR", str(tmp_path))

    path = await storage.save_resume(456, b"local bytes", "application/pdf", "r.pdf")
    assert storage.parse_resume_path(path) is None  # not a cloudinary path
    assert await storage.get_resume_url(path) is None

    await storage.delete_resume(456, path)
    assert not (tmp_path / "456").exists()
