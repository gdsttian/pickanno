import os
import json

from collections import OrderedDict
from glob import iglob
from tempfile import mkstemp

from flask import current_app as app

from pickanno import conf
from .standoff import parse_standoff


# TODO this doesn't need to be a class
class DocumentData(object):
    def __init__(self, text, annsets, metadata):
        self.text = text
        self.annsets = annsets
        self.metadata = metadata


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

    def get_documents(self, collection):
        documents = []
        collection_dir = os.path.join(self.root_dir, collection)
        for name in sorted(os.listdir(collection_dir)):
            path = os.path.join(collection_dir, name)
            if os.path.isfile(path):
                root, ext = os.path.splitext(name)
                if ext == '.txt':
                    documents.append(root)
        return documents

    def get_document_text(self, collection, document):
        path = os.path.join(self.root_dir, collection, document+'.txt')
        with open(path, encoding='utf-8') as f:
            return f.read()

    def get_document_annotation(self, collection, document, annset, parse=False):
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
