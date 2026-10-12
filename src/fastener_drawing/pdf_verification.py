"""Independent release gate outside FreeCAD: structure, labels and two renderers."""
import json
import subprocess
from pathlib import Path


def verify_pdf(pdf, drawing_report, directory, poppler):
    from pypdf import PdfReader
    from pypdf.generic import ContentStream
    import pypdfium2 as pdfium
    from PIL import Image, ImageChops, ImageFilter
    from .pdf_compatibility import repaired_operations

    pdf, directory = Path(pdf), Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(pdf, strict=True)
    if len(reader.pages) != 1:
        raise ValueError('Expected one verified native sheet')
    page = reader.pages[0]
    size = [float(page.mediabox.width), float(page.mediabox.height)]
    expected = [drawing_report['layout'][k]*72/25.4 for k in ('width_mm','height_mm')]
    if max(abs(a-b) for a,b in zip(size, expected)) > .01:
        raise ValueError('PDF physical sheet size differs from native plan')
    text = ''.join((page.extract_text() or '').split())
    labels = drawing_report['native_render_checks']['actual_dimension_labels']
    for label in labels:
        if ''.join(label.split()) not in text:
            raise ValueError('Missing verified dimension: '+label)
    if 'section' in drawing_report['layout']['positions']:
        hatch = drawing_report['section_diagnostics']['hatching']
        caption = 'AXIAL CUT A-A (UNHATCHED)' if hatch['status']=='requires_manual_completion' else 'SECTION A-A'
        if ''.join(caption.split()) not in text:
            raise ValueError('PDF section caption missing')
    if list(page.images):
        raise ValueError('Unexpected raster content in native vector drawing')
    _, changes = repaired_operations(list(ContentStream(page.get_contents(), reader).operations), page.get('/Resources', {}))
    if changes:
        raise ValueError('PDF still contains identified Qt export defects')
    prefix = directory/'poppler'
    completed = subprocess.run([str(poppler), '-scale-to','2000','-png','-singlefile',str(pdf),str(prefix)],
                               capture_output=True, text=True, timeout=60, creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (directory/'poppler.log').write_text(completed.stderr, encoding='utf-8')
    if completed.returncode or completed.stderr.strip():
        raise ValueError('PDF render failed or emitted diagnostics: '+completed.stderr[-2000:])
    with pdfium.PdfDocument(pdf) as document:
        bitmap = document[0].render(scale=2000/size[0])
        try:bitmap.to_pil().save(directory/'pdfium.png')
        finally:bitmap.close()
    with Image.open(str(prefix)+'.png') as first, Image.open(directory/'pdfium.png') as second:
        common=(min(first.width,second.width),min(first.height,second.height))
        if abs(first.width-second.width)>1 or abs(first.height-second.height)>1:
            raise ValueError('Independent renderer image sizes disagree')
        masks=[im.convert('L').crop((0,0,*common)).point(lambda x:255 if x<200 else 0) for im in (first,second)]
        counts=[sum(bool(x) for x in im.getdata()) for im in masks]
        unmatched=[sum(bool(x) for x in ImageChops.subtract(masks[i],masks[1-i].filter(ImageFilter.MaxFilter(5))).getdata()) for i in (0,1)]
    fractions=[n/max(c,1) for n,c in zip(unmatched,counts)]
    if min(counts)<100 or max(fractions)>.01:
        raise ValueError('Independent renderers disagree materially; manual review needed: '+str(fractions))
    result={'status':'passed', 'page_count':1, 'physical_size_points':size, 'verified_dimension_labels':labels,
            'identified_export_defects_remaining':0, 'poppler_warnings':0, 'vector_only':True,
            'renderer_comparison':{'dark_pixel_counts':counts,'unmatched_ink_beyond_two_pixels':unmatched,'unmatched_fraction':fractions,
                                   'maximum_allowed_fraction':.01,'basis':'Presentation discrepancy gate, not measurement or conformance proof'},
            'visual_review':'Required; two agreeing renderers can share an omitted drawing element',
            'nitro_review':'Not performed automatically; Phase 3.2 normalization contract retained'}
    (directory/'verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result
