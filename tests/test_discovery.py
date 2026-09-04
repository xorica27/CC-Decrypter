import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from cc_decrypter.discovery import (
    DraftVideo,
    find_protected_videos,
    output_path_for,
    probe_cryptor_type,
)


def box(box_type: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, "big") + box_type + payload


def bdve_footer(cryptor_type: int) -> bytes:
    crpt_payload = (
        cryptor_type.to_bytes(4, "big") + (3).to_bytes(4, "big") + b"\x11" * 32
    )
    return box(
        b"bdve",
        box(b"crpt", crpt_payload) + box(b"size", (68).to_bytes(4, "big")),
    )


def protected_bytes(cryptor_type: int = 1, payload: bytes = b"\x00" * 1024) -> bytes:
    return payload + bdve_footer(cryptor_type)


def plain_mp4_bytes() -> bytes:
    return b"\x00\x00\x00\x18ftypqt  \x00\x00\x02\x00qt  " + b"\x00" * 64


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write(self, relative: str, data: bytes) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_finds_protected_videos_in_nested_project_folders(self) -> None:
        first = self.write("0506/Resources/combination/a_video.mp4", protected_bytes())
        second = self.write("0707/Resources/combination/b_video.mp4", protected_bytes())

        results = find_protected_videos(self.root)

        self.assertEqual([video.path for video in results], [first, second])
        self.assertTrue(all(video.decryptable for video in results))
        self.assertEqual(results[0].project_name, "0506")
        self.assertEqual(
            results[0].relative, Path("0506/Resources/combination/a_video.mp4")
        )
        self.assertGreater(results[0].created, 0)

    def test_created_label_formats_birthtime(self) -> None:
        created = datetime(2026, 7, 7, 12, 0).timestamp()
        video = DraftVideo(
            path=Path("a.mp4"), relative=Path("a.mp4"), size=1, cryptor_type=1, created=created
        )

        self.assertEqual(video.created_label, "Jul 7, 2026")

    def test_created_label_empty_without_timestamp(self) -> None:
        video = DraftVideo(
            path=Path("a.mp4"), relative=Path("a.mp4"), size=1, cryptor_type=1, created=0.0
        )

        self.assertEqual(video.created_label, "")

    def test_skips_plain_mp4_and_non_video_files(self) -> None:
        self.write("project/clip.mp4.alpha.mp4", plain_mp4_bytes())
        self.write("project/notes.txt", protected_bytes())
        self.write("project/tiny.mp4", b"bdve")

        self.assertEqual(find_protected_videos(self.root), [])

    def test_lists_unsupported_cryptor_type_as_not_decryptable(self) -> None:
        path = self.write("project/clip_video.mp4", protected_bytes(cryptor_type=2))

        results = find_protected_videos(self.root)

        self.assertEqual([video.path for video in results], [path])
        self.assertEqual(results[0].cryptor_type, 2)
        self.assertFalse(results[0].decryptable)

    def test_probe_reads_only_tail_of_large_file(self) -> None:
        path = self.write(
            "project/clip_video.mp4", protected_bytes(payload=b"\x00" * (2 * 1024 * 1024))
        )

        self.assertEqual(probe_cryptor_type(path), 1)

    def test_probe_rejects_files_without_footer(self) -> None:
        path = self.write("project/clip.mp4", plain_mp4_bytes())

        self.assertIsNone(probe_cryptor_type(path))
        self.assertIsNone(probe_cryptor_type(self.root / "missing.mp4"))

    def test_skips_plain_file_that_still_carries_a_footer(self) -> None:
        self.write("project/clip.mp4", plain_mp4_bytes() + bdve_footer(1))

        self.assertEqual(find_protected_videos(self.root), [])

    def test_missing_folder_returns_empty(self) -> None:
        self.assertEqual(find_protected_videos(self.root / "nope"), [])

    def test_output_path_uses_project_and_avoids_collisions(self) -> None:
        video = DraftVideo(
            path=Path("/d/P/Resources/c/x_video.mp4"),
            relative=Path("P/Resources/c/x_video.mp4"),
            size=10,
            cryptor_type=1,
        )
        out_dir = self.root / "out"
        out_dir.mkdir()
        taken: set[str] = set()

        first = output_path_for(video, out_dir, taken)
        self.assertEqual(first.name, "P_x_video_decoded.mp4")
        self.assertEqual(first.parent, out_dir)

        first.write_bytes(b"")
        second = output_path_for(video, out_dir, taken)
        self.assertEqual(second.name, "P_x_video_decoded (2).mp4")

    def test_output_path_replaces_unsafe_project_characters(self) -> None:
        video = DraftVideo(
            path=Path("/d/a:b/video.mp4"),
            relative=Path("a:b/video.mp4"),
            size=10,
            cryptor_type=1,
        )

        result = output_path_for(video, self.root)

        self.assertEqual(result.name, "a_b_video_decoded.mp4")


if __name__ == "__main__":
    unittest.main()
