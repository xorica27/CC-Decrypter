import unittest

from cc_decrypter.decoder import CryptorParams, decode_bytes, param_sha256


def box(box_type: bytes, payload: bytes) -> bytes:
    return (len(payload) + 8).to_bytes(4, "big") + box_type + payload


def bdve_footer(params: CryptorParams) -> bytes:
    crpt_payload = (
        (1).to_bytes(4, "big")
        + (3).to_bytes(4, "big")
        + param_sha256(params.step, params.length, params.key)
    )
    return box(
        b"bdve",
        box(b"crpt", crpt_payload) + box(b"size", (68).to_bytes(4, "big")),
    )


def encrypt_bdve_payload(payload: bytes, params: CryptorParams) -> bytes:
    encrypted = bytearray(payload)
    for block_start in range(0, len(encrypted), params.step):
        block_end = min(block_start + params.length, len(encrypted))
        for offset in range(block_start, block_end):
            encrypted[offset] ^= params.key
    return bytes(encrypted)


def sample_table_moov(sample_offsets: list[int], sample_sizes: list[int]) -> bytes:
    hdlr = box(
        b"hdlr",
        b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00" + b"vide",
    )
    stsz = box(
        b"stsz",
        b"\x00\x00\x00\x00"
        + (0).to_bytes(4, "big")
        + len(sample_sizes).to_bytes(4, "big")
        + b"".join(size.to_bytes(4, "big") for size in sample_sizes),
    )
    stsc = box(
        b"stsc",
        b"\x00\x00\x00\x00"
        + (1).to_bytes(4, "big")
        + (1).to_bytes(4, "big")
        + len(sample_sizes).to_bytes(4, "big")
        + (1).to_bytes(4, "big"),
    )
    stco = box(
        b"stco",
        b"\x00\x00\x00\x00"
        + (1).to_bytes(4, "big")
        + sample_offsets[0].to_bytes(4, "big"),
    )
    stbl = box(b"stbl", stsc + stsz + stco)
    minf = box(b"minf", stbl)
    mdia = box(b"mdia", hdlr + minf)
    trak = box(b"trak", mdia)
    return box(b"moov", trak)


class DecoderTests(unittest.TestCase):
    def test_decodes_file_with_plain_moov_after_encrypted_mdat(self) -> None:
        first_sample = (1).to_bytes(4, "big") + b"\x65"
        second_sample = (1).to_bytes(4, "big") + b"\x41"
        mdat_payload = first_sample + second_sample
        sample_offsets = [36, 41]
        sample_sizes = [len(first_sample), len(second_sample)]
        payload = (
            box(b"ftyp", b"qt  " + b"\x00\x00\x02\x00" + b"qt  ")
            + box(b"wide", b"")
            + box(b"mdat", mdat_payload)
            + sample_table_moov(sample_offsets, sample_sizes)
        )
        params = CryptorParams(step=1000, length=41, key=0x55)
        protected = encrypt_bdve_payload(payload, params) + bdve_footer(params)

        decoded, decoded_params = decode_bytes(protected)

        self.assertEqual(decoded, payload)
        self.assertEqual(decoded_params, params)


if __name__ == "__main__":
    unittest.main()
