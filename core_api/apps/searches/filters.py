from opensearchpy import connections

from .documents import EventDocument, PostDocument, UserDocument

DOCUMENT_MAP = {
    'posts': PostDocument,
    'events': EventDocument,
    'users': UserDocument,
}

ALL_INDICES = 'posts_idx,events_idx,users_idx'

SEARCH_FIELDS = {
    'posts': ['body^2', 'tags^3', 'author_username'],
    'events': ['title^3', 'body^2', 'tags^3', 'location_name', 'author_username', 'category'],
    'users': ['username^3', 'display_name^2', 'bio', 'city'],
}


def _build_text_query(query, type_):
    if not query:
        return {'match_all': {}}

    if type_ and type_ in SEARCH_FIELDS:
        fields = SEARCH_FIELDS[type_]
    else:
        fields = list({
            field
            for fields_list in SEARCH_FIELDS.values()
            for field in fields_list
        })

    return {
        'multi_match': {
            'query': query,
            'fields': fields,
            'fuzziness': 'AUTO',
        }
    }


def _parse_facets(aggregations, type_):
    types_count = {'posts': 0, 'events': 0, 'users': 0}
    for bucket in aggregations.get('types_count', {}).get('buckets', []):
        key = bucket.get('key')
        if key in types_count:
            types_count[key] = bucket.get('doc_count', 0)

    posts_content_type_count = {'text': 0, 'image': 0, 'video': 0, 'audio': 0}
    content_buckets = (
        aggregations.get('posts_content_type_count', {})
        .get('by_content_type', {})
        .get('buckets', [])
    )
    for bucket in content_buckets:
        key = bucket.get('key')
        if key in posts_content_type_count:
            posts_content_type_count[key] = bucket.get('doc_count', 0)

    facets = {'types_count': types_count}
    if type_ in (None, 'posts'):
        facets['posts_content_type_count'] = posts_content_type_count
    return facets


def search_explore(query, type_=None, page=1, limit=20, content_type=None, lat=None, lon=None):
    client = connections.get_connection()
    index = DOCUMENT_MAP[type_].Index.name if type_ else ALL_INDICES
    offset = (page - 1) * limit

    text_query = _build_text_query(query, type_)
    filters = []

    if type_:
        filters.append({'term': {'doc_type': type_}})
    if content_type and (type_ == 'posts' or type_ is None):
        filters.append({'term': {'content_type': content_type}})
    if type_ == 'events' and lat and lon:
        filters.append({
            'geo_distance': {
                'distance': '50km',
                'location': {'lat': float(lat), 'lon': float(lon)},
            }
        })

    if filters:
        query_clause = {'bool': {'must': text_query, 'filter': filters}}
    else:
        query_clause = text_query

    body = {
        'from': offset,
        'size': limit,
        'query': query_clause,
        'sort': [
            '_score',
            {'sort_date': {'order': 'desc', 'unmapped_type': 'date'}},
        ],
        'aggs': {
            'types_count': {'terms': {'field': 'doc_type', 'size': 3}},
            'posts_content_type_count': {
                'filter': {'term': {'doc_type': 'posts'}},
                'aggs': {
                    'by_content_type': {
                        'terms': {'field': 'content_type', 'size': 4},
                    }
                },
            },
        },
    }

    response = client.search(index=index, body=body)
    total = response['hits']['total']['value']
    facets = _parse_facets(response.get('aggregations', {}), type_)

    hits = []
    for hit in response['hits']['hits']:
        source = hit.get('_source', {})
        source['_id'] = hit.get('_id')
        source['_score'] = hit.get('_score')
        hits.append(source)

    return hits, facets, total
