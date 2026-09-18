import unittest
from pathlib import Path

from desktop_simulator.platform_support import default_data_dir, qt_font_stack


class PlatformSupportTests(unittest.TestCase):
    def test_windows_uses_local_appdata_and_windows_fonts(self):
        self.assertEqual(default_data_dir('win32',{'LOCALAPPDATA':r'C:\\Users\\Alice\\AppData\\Local'},Path('/home/alice')),
                         Path(r'C:\\Users\\Alice\\AppData\\Local')/'Q3Q4_Simulator')
        self.assertIn('Microsoft YaHei UI',qt_font_stack('win32'))

    def test_macos_keeps_application_support_and_pingfang(self):
        self.assertEqual(default_data_dir('darwin',{},Path('/Users/alice')),Path('/Users/alice/Library/Application Support/Q3Q4_Simulator'))
        self.assertIn('PingFang SC',qt_font_stack('darwin'))


if __name__=='__main__':unittest.main(verbosity=2)
