# documents/gemini_chat.py

import re
from threading import Lock

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from django.conf import settings
from django.db.models import Q
from .models import Document, Tag


# ── Configure Gemini once at module load ────────────────────────────────────
GEMINI_API_KEYS = getattr(settings, 'GEMINI_API_KEYS', []) or []
GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', '').strip()
GEMINI_MODEL = getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash').strip() or 'gemini-1.5-flash'
_GENAI_LOCK = Lock()

_model = None
if genai and GEMINI_API_KEY:
    with _GENAI_LOCK:
        genai.configure(api_key=GEMINI_API_KEY)
    _model = genai.GenerativeModel(GEMINI_MODEL)


# ── System prompt that tells Gemini its role ────────────────────────────────
SYSTEM_PROMPT = """You are a helpful document assistant for a Paperless Document 
Management System. You have access to the user's document library, including 
document titles, categories, tags, notes, and full OCR-extracted text.

Your job is to answer questions about the user's documents accurately and helpfully.
You can:
- Summarize documents
- Find specific information within documents
- Compare content across multiple documents
- Answer questions based on the extracted text
- List documents by category, tag, or keyword
- Identify which documents contain specific information

Always base your answers on the document context provided. If the answer is not 
found in any document, say so clearly. Be concise but thorough.
Format your responses using markdown where appropriate (bullet points, bold, etc.)."""


_TAG_LISTING_RE = re.compile(r'\b(tag|tags|tagged)\b', re.IGNORECASE)
_LISTING_RE = re.compile(r'\b(list|show|display|find|which|what|all)\b', re.IGNORECASE)


def _is_tag_listing_request(user_query):
    """Detect requests that are asking for documents by tag rather than a normal Q&A answer."""
    if not user_query:
        return False

    if re.search(r'\btagged\b', user_query, re.IGNORECASE):
        return True

    return bool(
        _TAG_LISTING_RE.search(user_query)
        and (
            _LISTING_RE.search(user_query)
            or re.search(r'\b(by|with)\s+tag(s)?\b', user_query, re.IGNORECASE)
        )
    )


def _dedupe_titles(titles):
    seen = set()
    deduped = []
    for title in titles:
        if title not in seen:
            seen.add(title)
            deduped.append(title)
    return deduped


def _get_configured_api_keys():
    keys = []

    configured_keys = getattr(settings, 'GEMINI_API_KEYS', None)
    if isinstance(configured_keys, (list, tuple)):
        keys = [key.strip() for key in configured_keys if key and key.strip()]
    else:
        raw_key = getattr(settings, 'GEMINI_API_KEY', '').strip()
        if raw_key:
            keys = [key.strip() for key in re.split(r'[\n,;]+', raw_key) if key.strip()]

    deduped = []
    seen = set()
    for key in keys:
        if key not in seen:
            seen.add(key)
            deduped.append(key)

    return deduped


def _send_prompt_with_api_key(api_key, full_prompt, chat_history):
    if not genai:
        raise RuntimeError('google-generativeai is not installed.')

    with _GENAI_LOCK:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        chat_session = model.start_chat(history=chat_history)
        response = chat_session.send_message(full_prompt)

    return response.text


def _match_requested_tags(user_query, available_tags):
    """Return tags explicitly mentioned in the query, if any."""
    normalized_query = user_query.lower()
    matched_tags = []

    for tag in available_tags:
        tag_name = tag.name.strip().lower()
        if not tag_name:
            continue
        if re.search(rf'\b{re.escape(tag_name)}\b', normalized_query):
            matched_tags.append(tag)

    return matched_tags


def _build_tag_listing_response(user, requested_tags=None):
    """Build a direct markdown response for tag-listing requests."""
    tagged_docs = Document.objects.filter(uploaded_by=user).select_related('category').prefetch_related('tags')

    if requested_tags:
        requested_tag_ids = {tag.id for tag in requested_tags}
        tags_to_show = list(
            Tag.objects.filter(id__in=requested_tag_ids).order_by('name')
        )
    else:
        tags_to_show = list(
            Tag.objects.filter(documents__uploaded_by=user).distinct().order_by('name')
        )

    if not tags_to_show:
        return {
            'response': "I couldn't find any tagged documents in your library.",
            'docs_used': [],
            'error': None,
        }

    lines = ['### Documents grouped by tag', '']
    docs_used = []

    for tag in tags_to_show:
        docs = tagged_docs.filter(tags=tag).order_by('title')
        if not docs.exists():
            continue

        lines.append(f'**{tag.name}** ({docs.count()})')
        for doc in docs:
            docs_used.append(doc.title)
            category_suffix = f" — {doc.category.name}" if doc.category else ''
            lines.append(f'- {doc.title}{category_suffix}')
        lines.append('')

    if len(lines) == 2:
        return {
            'response': 'I found those tags, but no documents are attached to them yet.',
            'docs_used': [],
            'error': None,
        }

    return {
        'response': '\n'.join(lines).strip(),
        'docs_used': _dedupe_titles(docs_used),
        'error': None,
    }


def search_relevant_documents(user_query, user, max_docs=5):
    """
    Search the database for documents relevant to the user's query.
    Uses keyword matching across title, extracted_text, notes, and tags.
    Returns a queryset of the most relevant documents.
    """
    if not user_query.strip():
        return Document.objects.filter(uploaded_by=user).select_related('category').prefetch_related('tags')[:max_docs]

    # Extract meaningful words (ignore very short words)
    keywords = [w for w in user_query.lower().split() if len(w) > 2]

    if not keywords:
        return Document.objects.filter(uploaded_by=user).select_related('category').prefetch_related('tags')[:max_docs]

    # Build OR query across all searchable fields
    query_filter = Q()
    for keyword in keywords:
        query_filter |= Q(title__icontains=keyword)
        query_filter |= Q(extracted_text__icontains=keyword)
        query_filter |= Q(notes__icontains=keyword)
        query_filter |= Q(tags__name__icontains=keyword)
        query_filter |= Q(category__name__icontains=keyword)

    docs = Document.objects.filter(
        uploaded_by=user
    ).filter(query_filter).select_related('category').prefetch_related('tags').distinct()[:max_docs]

    # If no keyword matches, fall back to recent documents
    if not docs.exists():
        docs = Document.objects.filter(uploaded_by=user).select_related('category').prefetch_related('tags').order_by('-upload_date')[:max_docs]

    return docs


def build_context_string(documents, user):
    """
    Build a rich context string from the matched documents to send to Gemini.
    Truncates very large OCR text to stay within token limits.
    """
    all_docs = Document.objects.filter(uploaded_by=user)
    total_count = all_docs.count()

    lines = []
    lines.append(f"=== USER DOCUMENT LIBRARY ===")
    lines.append(f"Total documents in library: {total_count}")
    lines.append("")

    if not documents:
        lines.append("No documents found in the library.")
        return "\n".join(lines)

    lines.append(f"Showing {len(list(documents))} most relevant document(s):\n")

    for i, doc in enumerate(documents, 1):
        lines.append(f"--- DOCUMENT {i} ---")
        lines.append(f"Title       : {doc.title}")
        lines.append(f"Type        : {doc.file_type.upper()}")
        lines.append(f"Category    : {doc.category.name if doc.category else 'Uncategorized'}")
        lines.append(f"Tags        : {', '.join(t.name for t in doc.tags.all()) or 'None'}")
        lines.append(f"Uploaded    : {doc.upload_date.strftime('%d %b %Y')}")
        if doc.notes:
            lines.append(f"Notes       : {doc.notes}")

        # Include OCR text — truncate at 3000 chars per doc to avoid token overflow
        if doc.extracted_text and doc.extracted_text.strip():
            ocr_snippet = doc.extracted_text.strip()
            if len(ocr_snippet) > 3000:
                ocr_snippet = ocr_snippet[:3000] + "\n... [text truncated for brevity]"
            lines.append(f"Extracted Text:\n{ocr_snippet}")
        else:
            lines.append("Extracted Text: [No text extracted from this document]")

        lines.append("")  # blank line between docs

    return "\n".join(lines)


def get_chatbot_response(user_message, chat_history, user):
    """
    Main function called by the view.

    Args:
        user_message (str): The user's latest question.
        chat_history (list): List of {"role": "user"/"model", "parts": [text]} dicts.
        user: Django User object (to scope document queries).

    Returns:
        dict: {"response": str, "docs_used": list of doc titles, "error": str|None}
    """
    try:
        chat_history = chat_history or []

        if _is_tag_listing_request(user_message):
            all_tags = list(Tag.objects.filter(documents__uploaded_by=user).distinct().order_by('name'))
            requested_tags = _match_requested_tags(user_message, all_tags)
            return _build_tag_listing_response(user, requested_tags=requested_tags)

        api_keys = _get_configured_api_keys()
        if not api_keys:
            missing_bits = []
            if not genai:
                missing_bits.append('google-generativeai')
            missing_bits.append('GEMINI_API_KEY / GEMINI_API_KEYS')

            return {
                'response': '',
                'docs_used': [],
                'error': 'Gemini is not configured. Missing: ' + ', '.join(missing_bits),
            }

        # 1. Find relevant documents
        relevant_docs = search_relevant_documents(user_message, user)
        docs_used = [doc.title for doc in relevant_docs]

        # 2. Build the context
        context = build_context_string(relevant_docs, user)

        # 3. Build the full prompt for this turn
        full_prompt = f"""{SYSTEM_PROMPT}

{context}

User question: {user_message}

Please answer based on the documents above."""

        last_error = None
        for api_key in api_keys:
            try:
                response_text = _send_prompt_with_api_key(api_key, full_prompt, chat_history)
                return {
                    'response': response_text,
                    'docs_used': docs_used,
                    'error': None,
                }
            except Exception as exc:
                last_error = str(exc)

        return {
            'response': '',
            'docs_used': [],
            'error': f'Gemini API error after trying {len(api_keys)} key(s): {last_error}',
        }

    except Exception as e:
        return {
            "response": "",
            "docs_used": [],
            "error": f"Gemini API error: {str(e)}",
        }