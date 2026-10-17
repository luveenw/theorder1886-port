from paths import ROOT
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from patches import (compile_patches, external_patches, external_selection, compile_external,
                     game_profile, selected_patches, patch_requirements, GAMES)

ORDER = ROOT / 'patches/TheOrder1886-Orbis.xml'
ORDER_IDS = {'CUSA00035'}
SEGMENTS = [(0, 0x6000000)]


EXTERNAL = """<?xml version="1.0"?>
<Patch>
  <TitleID><ID>CUSA00035</ID></TitleID>
  <Metadata Title="The Order 1886" Name="On" Author="x" PatchVer="1.0" AppVer="01.02" AppElf="eboot.bin" isEnabled="true">
    <PatchList><Line Type="bytes" Address="0x00401000" Value="9090"/></PatchList>
  </Metadata>
  <Metadata Title="The Order 1886" Name="Off" Author="x" PatchVer="1.0" AppVer="01.02" AppElf="eboot.bin">
    <PatchList><Line Type="bytes32" Address="0x00402000" Value="0x12345678"/></PatchList>
  </Metadata>
  <Metadata Title="The Order 1886" Name="Mask" Author="x" PatchVer="1.0" AppVer="01.02" AppElf="eboot.bin" isEnabled="true">
    <PatchList><Line Type="mask" Value="90 ?? 90" Offset="0"/></PatchList>
  </Metadata>
  <Metadata Title="The Order 1886" Name="Old" Author="x" PatchVer="1.0" AppVer="01.00" AppElf="eboot.bin" isEnabled="true">
    <PatchList><Line Type="bytes" Address="0x00403000" Value="90"/></PatchList>
  </Metadata>
</Patch>"""


class ExternalPatchTests(unittest.TestCase):
    def test_native_1080_patch_sets_display_and_picture_size(self):
        # Actual 720p setup instructions: the upstream patch changes only the first
        # width/height pair, leaving the picture viewport at 720p.
        code = bytes.fromhex('a8807541c78584fcffff00050000c78588fcffffd0020000'
                             'c785d0fbffff00000000c785d4fbffff00000000'
                             'c785d8fbffff00050000c785dcfbffffd0020000')
        adapter = ROOT / 'patches/community/TheOrder1886-Native.xml'
        found = external_patches(adapter.parent, '01.02', ORDER, ORDER_IDS)
        selected = [row for row in found if row[0].endswith('/Native render resolution - 1080p')]
        self.assertEqual(len(selected), 1)
        image = bytearray(b'\0' * 16 + code + b'\0' * 16)
        writes = compile_external(selected, [(0, len(image))], image=bytes(image), reference_build=False)
        self.assertEqual(len(writes), 5)
        for offset, data in writes:
            image[offset:offset+len(data)] = data
        import struct
        self.assertEqual(image[18:20], b'\x90\x90')
        for offset in (10, 50): self.assertEqual(struct.unpack_from('<I', image, 16+offset)[0], 1920)
        for offset in (20, 60): self.assertEqual(struct.unpack_from('<I', image, 16+offset)[0], 1080)

    def test_other_build_requires_unique_signatures_for_every_write(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'external.xml'
            path.write_text(EXTERNAL)
            found = external_patches(path.parent, '01.02', ORDER, ORDER_IDS)
            meta = found[0][2]
            lines = list(meta.iter('Line'))
            lines[0].set('Pattern', '11 22 ?? 44 55 66')
            lines[0].set('At', '1')
            image = bytes.fromhex('00 11 22 33 44 55 66 00')
            self.assertEqual(compile_external(found[:1], [(0, len(image))],
                                              image=image, reference_build=False), [(2, b'\x90\x90')])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(compile_external(found[:1], [(0, 8)], image=image + image,
                                                  reference_build=False), [])
                lines[0].attrib.pop('Pattern')
                self.assertEqual(compile_external(found[:1], SEGMENTS, image=image,
                                                  reference_build=False), [])

    def test_selection_and_unsupported_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'extra.xml').write_text(EXTERNAL)
            (folder / 'other.xml').write_text(EXTERNAL.replace('CUSA00035', 'CUSA99999'))
            (folder / 'broken.xml').write_text('<Patch>')
            found = external_patches(folder, '01.02', ORDER, ORDER_IDS)
            self.assertEqual([key for key, _, _ in found],
                             ['extra.xml/On', 'extra.xml/Off', 'extra.xml/Mask'])
            # The file's isEnabled; the mask patch is skipped as a whole.
            writes = compile_external(external_selection(found, None), SEGMENTS)
            self.assertEqual(writes, [(0x1000, bytes.fromhex('9090'))])
            config = folder / 'patches.json'
            config.write_text('{"enabled": ["extra.xml/Off"], "disabled": ["extra.xml/On"]}')
            writes = compile_external(external_selection(found, config), SEGMENTS)
            self.assertEqual(writes, [(0x2000, (0x12345678).to_bytes(4, 'little'))])

    def test_built_in_file_is_not_external(self):
        self.assertEqual(external_patches(ORDER.parent, '01.02', ORDER, ORDER_IDS), [])


class GameProfileTests(unittest.TestCase):
    def test_profiles_by_title_id(self):
        self.assertEqual(game_profile('CUSA00035')[1:3], (ORDER, '01.02'))
        self.assertIsNone(game_profile('CUSA99999'))
        self.assertIsNone(game_profile(None))

    def test_unavailable_frame_rate_patch_falls_back_to_the_highest_lower_one(self):
        from graphics_options import restrict_to_available
        available = {'Skip Intro Logos', 'Frame Rate Patch - 60 FPS'}
        self.assertEqual(restrict_to_available(['Skip Intro Logos', 'Frame Rate Patch - 120 FPS'], available),
                         ['Skip Intro Logos', 'Frame Rate Patch - 60 FPS'])
        self.assertEqual(restrict_to_available(['Aspect Ratio - 32:9'], available), [])

    def test_defaults_and_extras(self):
        # Every built-in patch of The Order is off by default; the launcher's selection is exact.
        self.assertEqual(selected_patches(ORDER, '01.02', ''), [])
        self.assertEqual(selected_patches(ORDER, '01.02', 'Skip Intro Logos; Frame Rate Patch - 60 FPS'),
                         ['Skip Intro Logos', 'Frame Rate Patch - 60 FPS'])
        self.assertEqual(selected_patches(ORDER, '01.02', 'Skip Intro Logos', only=True), ['Skip Intro Logos'])
        self.assertEqual(selected_patches(ORDER, '01.00', '', only=True), [])
        with self.assertRaises(ValueError):
            selected_patches(ORDER, '01.02', 'Aspect Ratio - 16:9;Aspect Ratio - 21:9')

    def test_profile_by_title_for_any_region(self):
        from unittest import mock
        import patches
        self.assertEqual(game_profile('CUSA00070')[1], ORDER)
        self.assertEqual(game_profile('CUSA99999', 'The Order 1886™')[1], ORDER)
        self.assertIsNone(game_profile('CUSA99999', 'Another Game'))
        with mock.patch.object(patches, 'game_sfo', return_value={'TITLE_ID': 'CUSA77777', 'TITLE': 'The Order 1886'}):
            self.assertTrue(patches.game_patchable('folder'))
        self.assertFalse(patches.game_patchable(None))
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(patches.game_patchable(folder))  # no param.sfo: unknown game


class SignatureTests(unittest.TestCase):
    XML = """<?xml version="1.0"?>
<Patch>
  <Metadata Name="Found" AppVer="01.02">
    <PatchList><Line Type="bytes" Address="0x1004" Value="9090" Pattern="11 22 ?? 44 55 66" At="1"/></PatchList>
  </Metadata>
  <Metadata Name="Call" AppVer="01.02">
    <PatchList><Line Type="bytes" Address="0x1010" Value="e8{rel:there:0}" Pattern="aa bb cc dd ee" At="0"/></PatchList>
    <Target Name="there" Address="0x1100" Pattern="e9 ?? ?? ?? ?? 77 88" At="1" Ref="1"/>
  </Metadata>
  <Metadata Name="Missing" AppVer="01.02">
    <PatchList>
      <Line Type="bytes" Address="0x1004" Value="9090" Pattern="11 22 ?? 44 55 66" At="1"/>
      <Line Type="bytes" Address="0x1020" Value="90" Pattern="de ad be ef" At="0"/>
    </PatchList>
  </Metadata>
  <Metadata Name="Data" AppVer="01.02">
    <PatchList><Line Type="bytes32" Address="0x2000" Target="variable" Value="0x2"/></PatchList>
    <Target Name="variable" Address="0x2000" Pattern="44 89 35 ?? ?? ?? ?? c6" At="3" Ref="1"/>
  </Metadata>
</Patch>"""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.xml = Path(directory.name) / 'test.xml'
        self.xml.write_text(self.XML)
        image = bytearray(0x400)
        image[0x40:0x46] = bytes.fromhex('112233445566')
        image[0x80:0x85] = bytes.fromhex('aabbccddee')
        image[0x200:0x207] = bytes.fromhex('e9') + (0x300 - 0x205).to_bytes(4, 'little', signed=True) + bytes.fromhex('7788')
        # mov [rip+disp], r14d storing to 0x3f0, then the c6 of the next instruction.
        image[0x280:0x288] = bytes.fromhex('448935') + (0x3f0 - 0x287).to_bytes(4, 'little', signed=True) + b'\xc6'
        self.image = bytes(image)

    def test_sites_found_anywhere_and_rel32_recomputed(self):
        skipped = {}
        writes = compile_patches(self.xml, ['Found', 'Call', 'Missing'], None, [(0, 0x400)], self.image, skipped)
        call = (0x300 - (0x80 + 5)).to_bytes(4, 'little', signed=True)
        self.assertEqual(writes, [(0x41, b'\x90\x90'), (0x80, b'\xe8' + call)])
        # One site of the patch is missing: the whole patch is left out, with the reason.
        self.assertEqual(skipped, {'Missing': 'signature not found'})

    def test_ambiguous_signature_is_skipped(self):
        image = bytearray(self.image)
        image[0x100:0x106] = image[0x40:0x46]
        skipped = {}
        self.assertEqual(compile_patches(self.xml, ['Found'], None, [(0, 0x400)], bytes(image), skipped), [])
        self.assertEqual(skipped, {'Found': 'signature found more than once'})

    def test_without_the_image_the_reference_addresses_are_used(self):
        writes = compile_patches(self.xml, ['Found', 'Call'], '01.02', [(0, 0x10000)])
        self.assertEqual(writes[0], (0x1004, b'\x90\x90'))
        self.assertEqual(writes[1][0], 0x1010)

    def test_data_line_writes_at_its_target(self):
        # The variable has no bytes of its own to find: the code that stores to it points at it.
        self.assertEqual(compile_patches(self.xml, ['Data'], None, [(0, 0x400)], self.image, {}),
                         [(0x3f0, (2).to_bytes(4, 'little'))])
        self.assertEqual(compile_patches(self.xml, ['Data'], '01.02', [(0, 0x10000)]),
                         [(0x2000, (2).to_bytes(4, 'little'))])
        image = bytearray(self.image)
        image[0x280:0x288] = bytes(8)  # store not found: the whole patch is left out
        skipped = {}
        self.assertEqual(compile_patches(self.xml, ['Data'], None, [(0, 0x400)], bytes(image), skipped), [])
        self.assertEqual(skipped, {'Data': 'signature not found'})

    def test_requirements_from_patch_notes(self):
        # Notes ask for extra direct memory (shadPS4 "DMEM") and a VBlank rate.
        notes = self.xml.parent / 'notes.xml'
        notes.write_text('''<?xml version="1.0"?>
<Patch>
  <Metadata Name="Big" AppVer="01.02" Note="Requires setting DMEM to 6144 MB."><PatchList/></Metadata>
  <Metadata Name="Fast" AppVer="01.02" Note="Set VBlank to 120 FPS."><PatchList/></Metadata>
</Patch>''')
        self.assertEqual(patch_requirements(notes, ['Big'], '01.02'), (5056 + 6144, None))
        self.assertEqual(patch_requirements(notes, ['Fast'], '01.02'), (None, 120))
        self.assertEqual(patch_requirements(notes, [], '01.02'), (None, None))

    def test_original_aspect_restores_prepatched_fullscreen_setup(self):
        import struct
        # This dump already has the fullscreen float, even with no selected patch.
        image = bytes.fromhex('c7 85 18 fc ff ff 39 8e e3 3f '
                              'c7 85 d0 fb ff ff 00 00 00 00')
        writes = compile_patches(ORDER, ['Aspect Ratio - Original'], None,
                                 [(0, len(image))], image, {})
        self.assertEqual(writes, [(6, struct.pack('<f', 2.4))])

    def test_the_order_patches_compile(self):
        names = [m.get('Name') for m in ET.parse(ORDER).getroot().iter('Metadata')]
        self.assertTrue(compile_patches(ORDER, names, '01.02', [(0, 0x1800000)]))


if __name__ == '__main__':
    unittest.main()
