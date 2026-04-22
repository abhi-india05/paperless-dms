from django.contrib import admin
from .models import Document, Category, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'file_type', 'uploaded_by', 'category', 'upload_date')
    list_filter = ('file_type', 'category', 'upload_date')
    search_fields = ('title', 'extracted_text', 'notes')
    filter_horizontal = ('tags',)
    readonly_fields = ('upload_date', 'updated_at', 'extracted_text')
