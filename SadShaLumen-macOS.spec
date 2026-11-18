# macOS Apple silicon build (1.3.1): ONNX Runtime with Core ML, PyObjC Metal and the
# pure-Perl ExifTool.  Produces "dist/SadSha Lumen.app"; run it through tools/build_macos.sh,
# which draws build/macos/SadShaLumen.icns first and signs the bundle afterwards.
import os
import re
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

root = Path(SPECPATH)
version = re.search(r"__version__ = '([0-9.]+)'",
                    (root / 'lumen' / '__init__.py').read_text(encoding='utf-8')).group(1)
art = root / 'build' / 'macos'
minimum = os.environ.get('LUMEN_MACOS_MINIMUM', '15.0')

sys.path.insert(0, str(root))
from tools import bundle

raw_data, raw_binaries, raw_hidden = collect_all('rawpy')
ort_data, ort_binaries, ort_hidden = collect_all('onnxruntime', filter_submodules=bundle.runtime_module,
                                                 exclude_datas=bundle.ORT_EXCLUDED_DATAS)

# 1.8.0: float16-weight models, no bundled speech model, unused Qt pieces dropped (tools/bundle.py).
# The Perl ExifTool runs with /usr/bin/perl (Windows' exiftool.exe is not shipped).
assets = bundle.asset_datas(root, 'macos')
# 2.1.1: the AI models in Contents/…/models under their content names (lumen/ai_models.py).
assets += [(str(path), 'models') for path in bundle.model_files(root)]

a = Analysis(
    [str(root / 'main.py')], pathex=[str(root)],
    binaries=raw_binaries + ort_binaries,
    datas=assets + [(str(root / 'lumen' / 'locales'), 'lumen/locales')] + raw_data + ort_data + collect_data_files('tifffile'),
    hiddenimports=raw_hidden + ort_hidden + ['PIL.ImageCms', 'objc', 'Foundation', 'Metal', 'PySide6.QtMultimedia',
                                             'PySide6.QtNetwork'],
    excludes=bundle.EXCLUDES + ['windowsml'],
    noarchive=False,
)
a.binaries = bundle.trim(a.binaries, 'macos')
a.datas = bundle.trim(a.datas, 'macos')
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='SadShaLumen',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, disable_windowed_traceback=False, argv_emulation=False,
          target_arch='arm64', codesign_identity=None, entitlements_file=None)
# 1.6.0: Contents/MacOS/sadsha-lumen, the command line and the MCP server (stdio).
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name='sadsha-lumen',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=True, argv_emulation=False, target_arch='arm64', codesign_identity=None, entitlements_file=None)
coll = COLLECT(exe, cli, a.binaries, a.datas, strip=False, upx=False, name='SadShaLumen')

document = lambda name, types, rank='Alternate': {
    'CFBundleTypeName': name, 'CFBundleTypeRole': 'Editor', 'LSHandlerRank': rank, 'LSItemContentTypes': types}
exported = lambda identifier, description, extension: {
    'UTTypeIdentifier': identifier, 'UTTypeDescription': description, 'UTTypeConformsTo': ['public.json'],
    'UTTypeIconFile': 'SadShaLumen.icns', 'UTTypeTagSpecification': {'public.filename-extension': [extension]}}
app = BUNDLE(
    coll, name='SadSha Lumen.app', icon=str(art / 'SadShaLumen.icns'),
    bundle_identifier='com.sadsha.lumen', version=version,
    info_plist={
        'CFBundleName': 'SadSha Lumen',
        'CFBundleDisplayName': 'SadSha Lumen',
        'CFBundleShortVersionString': version,
        'CFBundleVersion': version,
        'CFBundleDevelopmentRegion': 'zh_CN',
        # 1.5.1: the interface languages, so native panels follow the same language list.
        'CFBundleLocalizations': ['zh_CN', 'zh_TW', 'en', 'ja', 'ko', 'de', 'fr', 'es', 'ru'],
        'CFBundleAllowMixedLocalizations': True,
        'LSMinimumSystemVersion': minimum,
        'LSArchitecturePriority': ['arm64'],
        'LSApplicationCategoryType': 'public.app-category.photography',
        # 2.3.0 (issue #11): sadsha-lumen is a console EXE in the same COLLECT, and PyInstaller turns that
        # into LSBackgroundOnly = true: the window opens but the app never becomes the active one, so
        # the menu bar stays on the previous app and key equivalents do not reach it.
        'LSBackgroundOnly': False,
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': 'SadSha Lumen · MIT License',
        # 1.5.0: voice instructions are recognized offline on this Mac.
        'NSMicrophoneUsageDescription': 'SadSha Lumen 在本机离线识别你的语音修图指令，录音不会上传。',
        # Every RAW type macOS knows (ARW, CR2 / CR3, NEF, RAF, RW2, DNG, ...) conforms to public.camera-raw-image.
        'CFBundleDocumentTypes': [
            document('Camera RAW', ['public.camera-raw-image']),
            document('Image', ['public.jpeg', 'public.png', 'public.tiff']),
            document('SadSha Lumen 工程', ['com.sadsha.lumen.project'], 'Owner'),
            document('SadSha Lumen 选片集', ['com.sadsha.lumen.album'], 'Owner'),
        ],
        'UTExportedTypeDeclarations': [
            exported('com.sadsha.lumen.project', 'SadSha Lumen 工程', 'lumen'),
            exported('com.sadsha.lumen.album', 'SadSha Lumen 选片集', 'lumenalbum'),
        ],
    },
)
