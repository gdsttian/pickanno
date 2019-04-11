import os
import sys
import re

from itertools import chain

from flask import current_app as app

from pickanno import conf
from .so2html import standoff_to_html


try:
    from fontTools.ttLib import TTFont
except ImportError:
    print('Failed `import fontTools`, try `pip3 install fonttools`',
          file=sys.stderr)
    raise


def visualize_annotation_sets(document_data):
    """Generate visualization of several annotation sets for the same text."""
    text = document_data.text
    annsets = document_data.annsets
    return [(k, standoff_to_html(text, a)) for k, a in annsets.items()]


def _find_covering_span(text, annsets, word_boundary=True):
    """Find text span covering giving annotation sets, optionally
    extending it to word boundaries."""
    flattened = [a for anns in annsets.values() for a in anns]
    start = min(a.start for a in flattened)
    end = max(a.end for a in flattened)
    if word_boundary and text[start].isalnum():
        while start > 0 and text[start-1].isalnum():
            start -= 1
    if word_boundary and text[end-1].isalnum():
        while end < len(text) and text[end].isalnum():
            end += 1
    return start, end


def visualize_candidates(document_data):
    """Generate visualization of alternative annotation candidates."""
    text = document_data.text
    data = document_data.metadata
    candidate_set = data['candidate_set']
    candidate_id = data['candidate_id']
    annsets = document_data.annsets

    # Find focused candidate and filter all annotation sets to overlapping
    candidate = _get_candidate(annsets, candidate_set, candidate_id)
    annsets = _filter_to_overlapping(annsets, candidate)

    # Identify span to center in the visualization
    span_start, span_end = _find_covering_span(text, annsets)

    # Split text to segments around centered span
    above, left, span, right, below = _split_text(text, span_start, span_end)

    # Adjust offsets for filtered annotations to zero at centered span start
    annsets = _adjust_offsets(annsets, span_start)

    so2html = standoff_to_html
    return {
        'above': so2html(above, []),
        'left': so2html(left, []),
        'spans': { k: so2html(span, a) for k, a in annsets.items() },
        'right': so2html(right, []),
        'below': so2html(below, []),
    }


def _adjust_offsets(annsets, offset):
    # TODO consider making copies instead of modifying annotations in place
    for key, annset in annsets.items():
        for a in annset:
            a.adjust_offsets(offset)
    return annsets


def _tokenize(text, reverse=False):
    if not reverse:
        tokens = re.split(r'(\s+)', text)
    else:
        text = text[::-1]
        rev_tokens = re.split(r'(\s+)', text)
        tokens = [t[::-1] for t in rev_tokens]
    return [t for t in tokens if t]


def _split_text(text, start, end, line_width=None):
    """Split text into five parts with reference to (start, end) span: (above,
    left, span, right, below), where (left, span, right) are on the
    same line.
    """
    if line_width is None:
        nontext_space = 10    # TODO figure out how much margins etc. take
        line_width = conf.get_line_width() - nontext_space

    span_text = text[start:end]
    span_width = _text_width(span_text)

    # add words to left and right until line width would be exceeded
    left_tokens = _tokenize(text[:start])
    right_tokens = _tokenize(text[end:], reverse=True)

    # trim candidate tokens to avoid including newlines in span
    def trim_tokens(tokens, filter_chars='\n'):
        trimmed = []
        for t in tokens:
            if any(c for c in filter_chars if c in t):
                trimmed = []
            else:
                trimmed.append(t)
        return trimmed
    right_tokens = trim_tokens(right_tokens)
    left_tokens = trim_tokens(left_tokens)
    
    left_text, right_text = '', ''
    left_width, right_width = 0, 0
    while True:
        if left_width <= right_width and left_tokens:
            new_text = left_tokens[-1] + left_text
            new_width = _text_width(new_text)
            if new_width + span_width + right_width < line_width:
                left_text = new_text
                left_width = new_width
                left_tokens.pop()
                continue
        if right_tokens:
            new_text = right_text + right_tokens[-1]
            new_width = _text_width(new_text)
            if left_width + span_width + new_width < line_width:
                right_text = new_text
                right_width = new_width
                right_tokens.pop()
                continue
        break

    above_text = text[:start-len(left_text)]
    below_text = text[end+len(right_text):]

    assert above_text+left_text+span_text+right_text+below_text == text

    # logging
    lw, sw, rw = (_text_width(t) for t in (left_text, span_text, right_text))
    tw = lw + sw + rw
    app.logger.info('_split_text(): split line "{}"---"{}"---"{}",'
                    'widths {}+{}+{}={}'.format(left_text, span_text,
                                                right_text, lw, sw, rw, tw))

    return above_text, left_text, span_text, right_text, below_text


def _text_width(text, point_size=None, font_file=None):
    """Return width of text in given point size and font."""
    if point_size is None:
        point_size = conf.get_font_size()
    if font_file is None:
        font_file = conf.get_font_file()
    if font_file not in _text_width.cache:
        font_path = os.path.join(app.root_path, 'static', 'fonts', font_file)
        _text_width.cache[font_file] = TTFont(font_path)
    ttfont = _text_width.cache[font_file]
    # Following https://stackoverflow.com/a/48357457
    cmap = ttfont['cmap']
    tcmap = cmap.getcmap(3,1).cmap
    glyphset = ttfont.getGlyphSet()
    units_per_em = ttfont['head'].unitsPerEm
    total = 0
    for c in text:
        if ord(c) in tcmap and tcmap[ord(c)] in glyphset:
            total += glyphset[tcmap[ord(c)]].width
        else:
            total += glyphset['.notdef'].width
    total_points = total * point_size / units_per_em
    return total_points
_text_width.cache = {}


def _get_candidate(annsets, candidate_set, candidate_id):
    """Return identified candidate annotation."""
    # Find candidate annotation 
    candidates = [t for t in annsets[candidate_set] if t.id == candidate_id]
    if not candidates:
        raise ValueError('missing {} in {}'.format(candidate_id, candidate_set))
    if len(candidates) > 1:
        raise ValueError('several {} in {}'.format(candidate_id, candidate_set))
    return candidates[0]


def _filter_to_overlapping(annsets, candidate):
    """Filter annsets to annotations overlapping candidate."""
    filtered = { k: [] for k in annsets }
    for key, annset in annsets.items():
        for a in annset:
            if a.overlaps(candidate):
                filtered[key].append(a)
    return filtered
