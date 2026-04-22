from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/',    views.login_view,    name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/',   views.logout_view,   name='logout'),

    # Core
    path('',                        views.dashboard_view,        name='dashboard'),
    path('upload/',                 views.upload_view,           name='upload'),
    path('search/',                 views.search_view,           name='search'),
    path('document/<int:pk>/',      views.document_detail_view,  name='document_detail'),
    path('document/<int:pk>/file/',  views.document_file_view,    name='document_file'),
    path('document/<int:pk>/delete/', views.document_delete_view, name='document_delete'),
    
        # ── Chatbot (new) ──
    path('chatbot/',      views.chatbot_view,     name='chatbot'),
    path('chatbot/ask/',  views.chatbot_ask_view, name='chatbot_ask'),
]
