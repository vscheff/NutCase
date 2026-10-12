"""Narrow, audited repair of two observed Qt PDF export defects.

Optional pypdf dependency; this module never imports FreeCAD. Measurements,
dimension placement and the editable CAD document are outside its scope.
Ambiguous instances of these defects fail rather than receiving guessed repairs.
"""
import hashlib
import io
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf import __version__ as pypdf_version
from pypdf.generic import ContentStream, FloatObject, IndirectObject, StreamObject


class UnsupportedPDF(ValueError):
    """The input does not satisfy the bounded repair contract."""


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_signature(value, ancestors=frozenset()):
    """Compare resolved resource content without relying on object numbers."""
    if isinstance(value, IndirectObject):
        key = (id(value.pdf), value.idnum, value.generation)
        if key in ancestors:
            raise UnsupportedPDF("Cyclic PDF resources are outside this repair contract")
        return object_signature(value.get_object(), ancestors | {key})
    if isinstance(value, dict):
        entries = {str(k): object_signature(v, ancestors) for k, v in value.items()
                   if not (isinstance(value, StreamObject) and k in ('/Length', '/Filter', '/DecodeParms'))}
        if isinstance(value, StreamObject):
            entries['decoded_stream_sha256'] = hashlib.sha256(value.get_data()).hexdigest()
        return entries
    if isinstance(value, (list, tuple)):
        return [object_signature(v, ancestors) for v in value]
    # PDF string bytes and numeric serialization matter, including glyph codes.
    data = io.BytesIO()
    value.write_to_stream(data)
    return data.getvalue().hex()


def operation_signature(operations):
    return [(object_signature(args), op.decode('ascii')) for args, op in operations]


def repaired_operations(operations, resources):
    """Keep the current path separate from q/Q graphics state, per PDF rules."""
    colors = resources.get('/ColorSpace', {})
    stack, spaces = [], {'fill': '/DeviceGray', 'stroke': '/DeviceGray'}
    current, clip_pending = False, False
    result, changes = [], []
    ending = (b'S', b's', b'f', b'F', b'f*', b'B', b'B*', b'b', b'b*', b'n')
    for index, (args, op) in enumerate(operations):
        if op == b'q':
            stack.append(dict(spaces))
        elif op == b'Q':
            if not stack:
                raise UnsupportedPDF('Graphics state stack underflow')
            spaces = stack.pop()
        elif op in (b'm', b're'):
            current = True
        elif op in (b'l', b'c', b'v', b'y') and not current:
            raise UnsupportedPDF('Path segment without a current point')
        elif op in (b'W', b'W*'):
            clip_pending = True
        elif op == b'h' and not current:
            # Only a pathless close followed immediately by a path terminator.
            # Keep the following fill/n, q/Q, clipping and transforms untouched.
            if args or clip_pending or index + 1 >= len(operations) or operations[index + 1][1] not in ending:
                raise UnsupportedPDF('Unrecognized pathless closepath context')
            changes.append({'operation_index': index, 'operator': 'h',
                            'action': 'remove_close_without_subpath'})
            continue
        elif op in ending:
            current, clip_pending = False, False
        elif op in (b'cs', b'CS'):
            if len(args) != 1:
                raise UnsupportedPDF('Malformed color-space selection')
            spaces['fill' if op == b'cs' else 'stroke'] = str(args[0])
        elif op in (b'g', b'rg', b'k', b'G', b'RG', b'K'):
            spaces['fill' if op.islower() else 'stroke'] = {
                b'g': '/DeviceGray', b'rg': '/DeviceRGB', b'k': '/DeviceCMYK'}[op.lower()]
        elif op in (b'scn', b'SCN', b'sc', b'SC'):
            space = spaces['fill' if op.islower() else 'stroke']
            resolved = colors.get(space, space)
            if hasattr(resolved, 'get_object'):
                resolved = resolved.get_object()
            required = {'/DeviceGray': 1, '/DeviceRGB': 3, '/DeviceCMYK': 4}.get(str(resolved))
            if required is not None and len(args) != required:
                if (op != b'SCN' or args or str(resolved) != '/DeviceRGB' or index == 0
                        or operations[index - 1][1] != b'CS'):
                    raise UnsupportedPDF('Unknown malformed color-setting operation')
                # CS resets the stroking color to the initial DeviceRGB black.
                # Make that already-selected color explicit; do not inherit or
                # guess the previous color, nor modify subsequent graphics state.
                args = [FloatObject(0), FloatObject(0), FloatObject(0)]
                changes.append({'operation_index': index, 'operator': 'SCN',
                                'action': 'explicit_DeviceRGB_initial_black', 'components': [0, 0, 0]})
        result.append((args, op))
    if stack or clip_pending:
        raise UnsupportedPDF('Unbalanced graphics state or unfinished clipping path')
    return result, changes


def normalize_pdf(source, target, expected_labels=()):
    """Write a separate PDF only after preservation checks; never edit source.

    Supports unencrypted native vector PDFs without annotations or XObjects.
    It is not a general PDF validator or universal compatibility guarantee.
    """
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target:
        raise ValueError('Use a separate output path; retain the original PDF')
    before_hash = digest(source)
    reader = PdfReader(source, strict=True)
    if reader.is_encrypted:
        raise UnsupportedPDF('Encrypted PDFs cannot be normalized')
    writer = PdfWriter(clone_from=reader)
    writer.pdf_header = reader.pdf_header
    page_reports = []
    for index, (old_page, page) in enumerate(zip(reader.pages, writer.pages)):
        if old_page.get('/Annots') and len(old_page['/Annots']):
            raise UnsupportedPDF('Interactive annotations are outside this repair contract')
        resources = old_page.get('/Resources', {})
        if resources.get('/XObject') and len(resources['/XObject']):
            raise UnsupportedPDF('Nested Form/Image XObjects require separate validation')
        original = list(ContentStream(old_page.get_contents(), reader).operations)
        corrected, changes = repaired_operations(original, resources)
        stream = ContentStream(page.get_contents(), writer)
        stream.operations = corrected
        page.replace_contents(stream)
        page_reports.append({'page_index': index, 'changes': changes,
                             'operation_count_before': len(original), 'operation_count_after': len(corrected)})
    data = io.BytesIO()
    writer.write(data)
    output = data.getvalue()
    check = PdfReader(io.BytesIO(output), strict=True)
    if len(check.pages) != len(reader.pages) or check.pdf_header != reader.pdf_header:
        raise RuntimeError('PDF version or page count changed')
    for old, new in zip(reader.pages, check.pages):
        original = ContentStream(old.get_contents(), reader).operations
        corrected, _ = repaired_operations(original, old.get('/Resources', {}))
        actual = ContentStream(new.get_contents(), check).operations
        if operation_signature(corrected) != operation_signature(actual):
            raise RuntimeError('Valid drawing operators changed during serialization')
        for key in set(old.keys()) | set(new.keys()):
            if key not in ('/Parent', '/Contents') and object_signature(old.get(key)) != object_signature(new.get(key)):
                raise RuntimeError('PDF page or resources changed: ' + str(key))
        if old.extract_text() != new.extract_text():
            raise RuntimeError('Dimension or caption text changed')
    compact = ''.join(''.join(page.extract_text() or '' for page in check.pages).split())
    for label in expected_labels:
        if ''.join(label.split()) not in compact:
            raise RuntimeError('Missing expected dimension label: ' + label)
    if digest(source) != before_hash:
        raise RuntimeError('Source PDF changed during normalization')
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.pending')
    try:
        temporary.write_bytes(output)
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {'source': str(source), 'source_sha256': before_hash, 'output': str(target),
            'normalizer': 'fastener_drawing.pdf_compatibility', 'pypdf_version': pypdf_version,
            'output_sha256': hashlib.sha256(output).hexdigest(), 'pdf_version': check.pdf_header,
            'page_count': len(check.pages), 'pages': page_reports,
            'expected_dimension_labels': list(expected_labels),
            'valid_operators_and_positions_preserved': True, 'resolved_resources_preserved': True,
            'font_streams_and_glyph_mappings_preserved': True, 'page_properties_preserved': True,
            'extracted_text_identical': True, 'vector_content_preserved': True,
            'original_preserved': True, 'viewer_verification': 'required separately',
            'scope': 'Two identified Qt export defects; not a general PDF conformance validator'}
