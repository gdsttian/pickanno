import os
import json

from collections import OrderedDict, defaultdict
from glob import iglob
from tempfile import mkstemp

from flask import current_app as app

from pickanno import conf
from .standoff import parse_standoff


class DocumentData(object):
    """Text with alternative annotation sets, designated candidate
    annotation, and possible judgments."""
    def __init__(self, text, annsets, metadata):
        self.text = text
        self.annsets = annsets
        self.metadata = metadata
        self.candidate = self.get_annotation(self.candidate_annset,
                                             self.candidate_id)

    def accepted_annsets(self):
        return self.metadata.get('accepted', [])

    def rejected_annsets(self):
        return self.metadata.get('rejected', [])

    def judgment_complete(self):
        judged = set(self.accepted_annsets()) | set(self.rejected_annsets())
        return not any (a for a in self.annsets if not a in judged)

    def filter_to_candidate(self):
        """Filter annsets to annotations overlapping candidate."""
        filtered = { k: [] for k in self.annsets }
        for key, annset in self.annsets.items():
            for a in annset:
                if a.overlaps(self.candidate):
                    filtered[key].append(a)
        self.annsets = filtered

    def annotated_strings(self, unique=True, include_empty=False):
        flattened = [a for anns in self.annsets.values() for a in anns]
        texts = [a.text for a in flattened]
        if not include_empty:
            texts = [t for t in texts if t]
        if unique:
            texts = list(OrderedDict.fromkeys(texts))
        return texts

    @property
    def candidate_annset(self):
        return self.annsets[self.metadata['candidate_set']]

    @property
    def candidate_id(self):
        return self.metadata['candidate_id']

    @staticmethod
    def get_annotation(annset, id_):
        """Return identified annotation."""
        matching = [t for t in annset if t.id == id_]
        if not matching:
            raise KeyError('annotation {} not found'.format(id_))
        if len(matching) > 1:
            raise ValueError('duplicate annoation id {}'.format(id_))
        return matching[0]


class FilesystemData(object):
    def __init__(self, root_dir):
        self.root_dir = root_dir

    def get_collections(self):
        subdirs = []
        for name in sorted(os.listdir(self.root_dir)):
            path = os.path.join(self.root_dir, name)
            if os.path.isdir(path):
                subdirs.append(name)
        return subdirs

    def _get_contents_by_ext(self, collection):
        """Get collection contents organized by file extension."""
        contents_by_ext = defaultdict(list)
        collection_dir = os.path.join(self.root_dir, collection)
        for name in sorted(os.listdir(collection_dir)):
            path = os.path.join(collection_dir, name)
            if os.path.isfile(path):
                root, ext = os.path.splitext(name)
                contents_by_ext[ext].append(root)
        return contents_by_ext

    def get_documents(self, collection, include_status=False):
        contents_by_ext = self._get_contents_by_ext(collection)
        documents = contents_by_ext['.txt']
        if not include_status:
            # simple listing
            return documents
        else:
            statuses = []
            for root in documents:
                try:
                    document_data = self.get_document_data(collection, root)
                    if document_data.judgment_complete():
                        status = app.config['STATUS_COMPLETE']
                    else:
                        status = app.config['STATUS_INCOMPLETE']
                except:
                    status = app.config['STATUS_ERROR']
                statuses.append(status)
            return documents, statuses

    def get_neighbouring_documents(self, collection, document):
        documents = self.get_documents(collection)
        doc_idx = documents.index(document)
        prev_doc = None if doc_idx == 0 else documents[doc_idx-1]
        next_doc = None if doc_idx == len(documents)-1 else documents[doc_idx+1]
        return prev_doc, next_doc

    def get_document_text(self, collection, document):
        path = os.path.join(self.root_dir, collection, document+'.txt')
        with open(path, encoding='utf-8') as f:
            return f.read()

    def get_document_annotation(self, collection, document, annset,
                                parse=False):
        path = os.path.join(self.root_dir, collection, document+'.'+annset)
        with open(path, encoding='utf-8') as f:
            data = f.read()
        if not parse:
            return data
        else:
            return parse_standoff(data)

    def get_document_metadata(self, collection, document):
        path = os.path.join(self.root_dir, collection, document+'.json')
        with open(path, encoding='utf-8') as f:
            return json.load(f)

    def get_document_data(self, collection, document):
        root_path = os.path.join(self.root_dir, collection, document)
        glob_path = root_path + '.*'

        extensions = set()
        for path in iglob(glob_path):
            root, ext = os.path.splitext(os.path.basename(path))
            assert ext[0] == '.'
            ext = ext[1:]
            extensions.add(ext)
        app.logger.info('Found {} for {}'.format(extensions, glob_path))

        for ext in ('txt', 'ann1', 'ann2', 'json'):
            if ext not in extensions:
                raise KeyError('missing {}.{}'.format(root_path, ext))

        text = self.get_document_text(collection, document)
        metadata = self.get_document_metadata(collection, document)
        annsets = OrderedDict()
        for key in ('ann1', 'ann2'):
            annsets[key] = self.get_document_annotation(
                collection, document, key, parse=True)

        return DocumentData(text, annsets, metadata)

    def set_document_picks(self, collection, document, accepted, rejected):
        data = self.get_document_metadata(collection, document)
        data['accepted'] = accepted
        data['rejected'] = rejected
        path = os.path.join(self.root_dir, collection, document+'.json')
        self.safe_write_file(path, json.dumps(data, indent=4, sort_keys=True))

    @staticmethod
    def safe_write_file(fn, text):
        """Atomic write using os.rename()."""
        fd, tmpfn = mkstemp()
        with open(fd, 'wt') as f:
            f.write(text)
            # https://stackoverflow.com/a/2333979
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmpfn, fn)

    @staticmethod
    def read_ann(path, parse=True):
        with open(path, encoding='utf-8') as f:
            data = f.read()
        if not parse:
            return data
        else:
            return parse_standoff(data, path)


def get_db():
    data_dir = conf.get_datadir()
    return FilesystemData(data_dir)


def close_db(err=None):
    pass


def init(app):
    app.teardown_appcontext(close_db)
