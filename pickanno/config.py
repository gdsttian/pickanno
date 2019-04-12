from pickanno.protocol import *


DATADIR = 'data'

# Visualization configuration

FONT_SIZE = 16    # pixels
FONT_FILE = 'OpenSans-Regular.ttf'    # filename in static/fonts
FONT_FAMILY = 'Open Sans'             # font-family in css
LINE_WIDTH = 800    # pixels, for visualizations

# Add abbreviated type as subscript to spans

ANNOTATION_TYPE_SUBSCRIPT = False # True

# Highlight context mentions of candidate annotations

HIGHLIGHT_CONTEXT_MENTIONS = True

# Key binding configuration

HOTKEYS = {
    'ArrowUp': PICK_FIRST,    # pick first candidate
    'ArrowDown': PICK_LAST,   # pick last candidate
    'ArrowRight': PICK_ALL,   # accept all candidates
    'ArrowLeft': PICK_NONE,   # reject all candidates
    'z': CLEAR_PICKS,         # clear accept/reject
}

# Search links to add for candidate annotation strings

SEARCH_CONFIG = [
    ('Google', 'https://www.google.com/search?q='),
    ('Wikipedia', 'http://en.wikipedia.org/wiki/Special:Search?search=')
]

# Document status constants (TODO: maybe not the right place for these)

STATUS_COMPLETE = 'complete'
STATUS_INCOMPLETE = 'todo'
STATUS_ERROR = 'ERROR'
