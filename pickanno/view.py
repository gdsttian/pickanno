from flask import Blueprint
from flask import request, render_template, jsonify
from flask import current_app as app

from .db import get_db
from .visualize import visualize_candidates, visualize_annotation_sets
from .protocol import PICK_FIRST, PICK_LAST, PICK_ALL, PICK_NONE

bp = Blueprint('view', __name__, static_folder='static', url_prefix='/pickanno')


@bp.route('/')
def root():
    return show_collections()


@bp.route('/')
def show_collections():
    db = get_db()
    collections = db.get_collections()
    return render_template('collections.html', collections=collections)


@bp.route('/collection/<collection>/')
def show_collection(collection):
    db = get_db()
    documents = db.get_documents(collection)
    return render_template(
        'documents.html',
        collection=collection,
        documents=documents
    )


@bp.route('/collection/<collection>/<document>.txt')
def show_text(collection, document):
    db = get_db()
    return db.get_document_text(collection, document)


@bp.route('/collection/<collection>/<document>.ann<idx>')
def show_annotation_set(collection, document, idx):
    db = get_db()
    return db.get_document_annotation(collection, document, 'ann'+idx)


@bp.route('/collection/<collection>/<document>.json')
def show_metadata(collection, document):
    db = get_db()
    return jsonify(db.get_document_metadata(collection, document))


@bp.route('/collection/<collection>/<document>.all')
def show_all_annotations(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    content = visualize_annotation_sets(document_data)
    return render_template('visualization.html', collection=collection,
                           document=document, content=content)


@bp.route('/collection/<collection>/<document>')
def show_alternative_annotations(collection, document):
    db = get_db()
    document_data = db.get_document_data(collection, document)
    content = visualize_candidates(document_data)
    return render_template('pickanno.html', collection=collection,
                           document=document, content=content,
                           metadata=document_data.metadata)


@bp.route('/collection/<collection>/<document>/pick')
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
