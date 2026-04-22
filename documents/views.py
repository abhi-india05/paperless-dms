import mimetypes
import tempfile
from io import BytesIO
from pathlib import Path
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .gemini_chat import get_chatbot_response

from .models import Document, Category, Tag
from .forms import LoginForm, RegisterForm, DocumentUploadForm, SearchForm
from .ocr import extract_text_from_file


def _extract_text_from_uploaded_bytes(file_bytes, file_name):
    suffix = Path(file_name).suffix or '.bin'
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        return extract_text_from_file(temp_path)
    finally:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


def _document_file_response(document, download=False):
    file_bytes = document.file_data

    if not file_bytes and document.file_name:
        legacy_path = Path(settings.MEDIA_ROOT) / document.file_name
        if legacy_path.exists():
            file_bytes = legacy_path.read_bytes()

    if not file_bytes:
        raise Http404('Document file is missing.')

    filename = document.get_download_filename()
    content_type = document.file_mime_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    response = FileResponse(BytesIO(file_bytes), content_type=content_type)
    disposition = 'attachment' if download else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


# ──────────────────────────────────────────────────────────────────────────────
# Authentication Views
# ──────────────────────────────────────────────────────────────────────────────

def login_view(request):
    """Handle user login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    else:
        form = LoginForm()

    return render(request, 'documents/login.html', {'form': form})


def register_view(request):
    """Handle new user registration."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account created! Welcome, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()

    return render(request, 'documents/register.html', {'form': form})


def logout_view(request):
    """Log out the current user."""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    """Show user's documents with optional category/tag filtering."""
    documents = Document.objects.filter(uploaded_by=request.user).select_related('category')
    categories = Category.objects.all()
    tags = Tag.objects.all()

    # Filter by category
    category_id = request.GET.get('category')
    if category_id:
        documents = documents.filter(category__id=category_id)

    # Filter by tag
    tag_id = request.GET.get('tag')
    if tag_id:
        documents = documents.filter(tags__id=tag_id)

    # Quick stats
    total_docs = Document.objects.filter(uploaded_by=request.user).count()
    pdf_count = Document.objects.filter(uploaded_by=request.user, file_type='pdf').count()
    img_count = Document.objects.filter(uploaded_by=request.user).filter(
        Q(file_type='jpg') | Q(file_type='png')
    ).count()

    context = {
        'documents': documents,
        'categories': categories,
        'tags': tags,
        'selected_category': category_id,
        'selected_tag': tag_id,
        'total_docs': total_docs,
        'pdf_count': pdf_count,
        'img_count': img_count,
    }
    return render(request, 'documents/dashboard.html', context)


# ──────────────────────────────────────────────────────────────────────────────
# Document Upload
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def upload_view(request):
    """Handle document upload with OCR processing."""
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user

            # Determine file type from extension
            uploaded_file = form.cleaned_data['file']
            file_bytes = uploaded_file.read()
            ext = Path(uploaded_file.name).suffix.lower().lstrip('.')
            document.file_type = 'jpg' if ext == 'jpeg' else ext
            document.file_name = uploaded_file.name
            document.file_mime_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream'
            document.file_data = file_bytes

            # Save the file bytes in MySQL before running OCR.
            document.save()

            # Run OCR against a temporary file so the uploaded file still lives only in MySQL.
            extracted = _extract_text_from_uploaded_bytes(file_bytes, uploaded_file.name)
            document.extracted_text = extracted
            document.save()

            # Handle comma-separated tags
            tags_input = form.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [t.strip().lower() for t in tags_input.split(',') if t.strip()]
                for tag_name in tag_names:
                    tag_obj, _ = Tag.objects.get_or_create(name=tag_name)
                    document.tags.add(tag_obj)

            ocr_status = 'Text extracted successfully.' if extracted else 'No text could be extracted (OCR returned empty).'
            messages.success(request, f'Document "{document.title}" uploaded! {ocr_status}')
            return redirect('dashboard')
        else:
            messages.error(request, 'Upload failed. Please check the form below.')
    else:
        form = DocumentUploadForm()

    return render(request, 'documents/upload.html', {'form': form})


# ──────────────────────────────────────────────────────────────────────────────
# Search
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def search_view(request):
    """Full-text keyword search across titles, extracted text, and notes."""
    form = SearchForm(request.GET or None)
    results = []
    query = ''
    searched = False

    if request.GET:
        searched = True
        if form.is_valid():
            query = form.cleaned_data.get('query', '')
            category = form.cleaned_data.get('category')
            tag = form.cleaned_data.get('tag')

            qs = Document.objects.filter(uploaded_by=request.user).select_related('category')

            if query:
                qs = qs.filter(
                    Q(title__icontains=query) |
                    Q(extracted_text__icontains=query) |
                    Q(notes__icontains=query) |
                    Q(tags__name__icontains=query)
                ).distinct()

            if category:
                qs = qs.filter(category=category)

            if tag:
                qs = qs.filter(tags=tag)

            results = qs

    context = {
        'form': form,
        'results': results,
        'query': query,
        'searched': searched,
        'result_count': len(results) if searched else 0,
    }
    return render(request, 'documents/search.html', context)


# ──────────────────────────────────────────────────────────────────────────────
# Document Detail
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def document_detail_view(request, pk):
    """Show full details and extracted text of a single document."""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    return render(request, 'documents/document_detail.html', {'document': document})


@login_required
def document_file_view(request, pk):
    """Stream the uploaded file directly from MySQL."""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)
    download = request.GET.get('download') == '1'
    return _document_file_response(document, download=download)


# ──────────────────────────────────────────────────────────────────────────────
# Document Delete
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def document_delete_view(request, pk):
    """Delete a document and its associated file."""
    document = get_object_or_404(Document, pk=pk, uploaded_by=request.user)

    if request.method == 'POST':
        title = document.title
        document.delete()
        messages.success(request, f'Document "{title}" has been deleted.')
        return redirect('dashboard')

    return render(request, 'documents/document_confirm_delete.html', {'document': document})


# ──────────────────────────────────────────────────────────────────────────────
# Chatbot Views
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def chatbot_view(request):
    """Render the chatbot page and initialize session history."""
    # Clear chat history when the page is freshly loaded via GET
    if request.method == 'GET':
        request.session['chat_history'] = []
    return render(request, 'documents/chatbot.html')


@login_required
@require_POST
def chatbot_ask_view(request):
    """
    AJAX endpoint. Receives a JSON body with {"message": "..."}, 
    calls Gemini with document context, returns JSON response.
    """
    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'error': 'Invalid request body.'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty.'}, status=400)

    # Load chat history from session (persists across AJAX calls in same session)
    chat_history = request.session.get('chat_history', [])

    # Call Gemini
    result = get_chatbot_response(user_message, chat_history, request.user)

    if result['error']:
        return JsonResponse({'error': result['error']}, status=500)

    # Update session history with this turn
    # Gemini expects {"role": "user"/"model", "parts": ["text"]}
    chat_history.append({"role": "user",  "parts": [user_message]})
    chat_history.append({"role": "model", "parts": [result['response']]})

    # Keep only last 20 turns (10 exchanges) to avoid session bloat
    if len(chat_history) > 20:
        chat_history = chat_history[-20:]

    request.session['chat_history'] = chat_history
    request.session.modified = True

    return JsonResponse({
        'response': result['response'],
        'docs_used': result['docs_used'],
    })