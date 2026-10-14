"""Retain primary release, build and license evidence; failed requests stay visible."""
import concurrent.futures
import json
from research import OUT, fetch, digest

URLS = {
 'qtwebengine-tags.json':'https://api.github.com/repos/qt/qtwebengine/tags?per_page=20',
 'qtwebengine-download.html':'https://download.qt.io/official_releases/qtwebengine/',
 'qt6140-download.html':'https://download.qt.io/official_releases/qt/6.140/6.140.0/submodules/',
 'qt-webengine-separate.html':'https://www.qt.io/blog/qt-webengine-will-release-separate',
 'pdfium-release.json':'https://api.github.com/repos/bblanchon/pdfium-binaries/releases/tags/chromium%2F8076',
 'pdfium-build-tag.json':'https://api.github.com/repos/bblanchon/pdfium-binaries/git/ref/tags/chromium%2F8076',
 'ms-redistribution.html':'https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170',
 'ms-redist-list.html':'https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution',
 'ms-runtime-download.html':'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170',
 'qt-lgpl-obligations.html':'https://www.qt.io/development/open-source-lgpl-obligations',
 'qt-sbom.html':'https://doc.qt.io/qt-6/sbom.html',
 'qt-windows-build.html':'https://doc.qt.io/qt-6/windows-building.html',
 'qt-qtpdf-pdfium.html':'https://doc-snapshots.qt.io/qtpdf/qtpdf-3rdparty-pdfium.html',
 'qt-licenses.html':'https://doc.qt.io/qt-6/licenses-used-in-qt.html',
 'qt-opengl-software.html':'https://doc.qt.io/qt-6/windows-graphics.html',
 'pyside-community.html':'https://doc.qt.io/qtforpython-6/commercial/index.html',
 'gnu-gpl2.html':'https://www.gnu.org/licenses/old-licenses/gpl-2.0.html',
 'gnu-lgpl3.html':'https://www.gnu.org/licenses/lgpl-3.0.html',
 'gnu-gpl3.html':'https://www.gnu.org/licenses/gpl-3.0.html',
}


def main():
    def work(item):
        filename,url=item
        try:
            path=fetch(url,OUT/'research'/filename)
            return {'file':filename,'url':url,'sha256':digest(path),'status':'ACQUIRED'}
        except Exception as error:
            return {'file':filename,'url':url,'status':'BLOCKED','error':str(error)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        records=list(pool.map(work,URLS.items()))
    (OUT/'research/primary-reference-manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    for row in records:print(row['file'],row['status'],row.get('error',''))


if __name__=='__main__':main()
