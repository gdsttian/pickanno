from flask import Blueprint
from flask import request, url_for, render_template, jsonify
from flask import current_app as app

from .db import get_db
from .visualize import visualize_candidates, visualize_annotation_sets
from .visualize import visualize_legend
from .protocol import PICK_FIRST, PICK_LAST, PICK_ALL, PICK_NONE, CLEAR_PICKS

bp = Blueprint('view', __name__, static_folder='static', url_prefix='/pickanno')


@bp.route('/')
def root():
    return show_collections()


@bp.route('/')
def show_collections():
    db = get_db()
    collections = db.get_collections()
    return render_template('collections.html', collections=collections)


@bp.route('/<collection>/')
def show_collection(collection):
    db = get_db()
    documents = db.get_documents(collection)
    return render_template(
        'documents.html',
        collection=collection,
        documents=documents
    )


@bp.route('/<collection>/<document>.txt')
def show_text(collection, document):
    db = get_db()
    return db.get_document_text(collection, document)


@bp.route('/<collection>/<document>.ann<idx>')
def show_annotation_set(collection, document, idx):
    db = get_db()
    return db.get_document_annotation(collection, document, 'ann'+idx)


@bp.route('/<collection>/<document>.json')
def show_metadata(collection, document):
    db = get_db()
    return jsonify(db.get_document_metadata(collection, document))


def _prev_and_next_url(endpoint, collection, document):
    # navigation helper
    db = get_db()
    prev_doc, next_doc = db.get_neighbouring_documents(collection, document)
    prev_url, next_url = (
        url_for(endpoint, collection=collection, document=d) if d is not None
        else None
        for d in (prev_doc, next_doc)
    )
    return prev_url, next_url


@bp.route('/<collection>/<document>.all')
def show_all_annotations(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    content = visualize_annotation_sets(document_data)
    legend = visualize_legend(document_data)
    prev_url, next_url = _prev_and_next_url(
        request.endpoint, collection, document)
    return render_template('annsets.html', **locals())


@bp.route('/<collection>/<document>')
def show_alternative_annotations(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    # Filter to avoid irrelevant types in legend
    document_data.filter_to_candidate()
    metadata = document_data.metadata
    content = visualize_candidates(document_data)
    legend = visualize_legend(document_data)
    prev_url, next_url = _prev_and_next_url(
        request.endpoint, collection, document)
    return render_template('pickanno.html', **locals())


@bp.route('/<collection>/<document>/pick')
def pick_annotation(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    keys = list(document_data.annsets.keys())
    choice = request.args.get('choice')
    if choice == PICK_NONE:
        accepted, rejected = [], keys
    elif choice == PICK_FIRST:
        accepted, rejected = [keys[0]], keys[1:]
    elif choice == PICK_LAST:
        accepted, rejected = [keys[-1]], keys[:-1]
    elif choice == PICK_ALL:
        accepted, rejected = keys, []
    elif choice == CLEAR_PICKS:
        accepted = rejected = [], []
    elif choice in keys:
        accepted, rejected = [choice], [k for k in keys if k != choice]
    else:
        app.logger.error('invalid choice {}'.format(choice))

    app.logger.info('{}/{}: accepted {}, rejected {}'.format(
        collection, document, accepted, rejected))
    db.set_document_picks(collection, document, accepted, rejected)

    # Make sure the DB agrees
    data = db.get_document_metadata(collection, document)

    return jsonify({
        'accepted': data['accepted'],
        'rejected': data['rejected'],
    })
