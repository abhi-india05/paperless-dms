from pathlib import Path

from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Document(models.Model):
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('jpg', 'JPG'),
        ('png', 'PNG'),
    ]

    title = models.CharField(max_length=255)
    file_data = models.BinaryField()
    file_name = models.CharField(max_length=255, blank=True, default='')
    file_mime_type = models.CharField(max_length=100, blank=True, default='')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    tags = models.ManyToManyField(Tag, blank=True, related_name='documents')
    extracted_text = models.TextField(blank=True, default='')
    notes = models.TextField(blank=True, default='')
    upload_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-upload_date']

    def __str__(self):
        return self.title

    def get_download_filename(self):
        if self.file_name:
            return Path(self.file_name).name
        suffix = f'.{self.file_type}' if self.file_type else ''
        return f'{self.title}{suffix}'

    def get_file_icon(self):
        icons = {
            'pdf': 'bi-file-earmark-pdf-fill text-danger',
            'jpg': 'bi-file-earmark-image-fill text-success',
            'png': 'bi-file-earmark-image-fill text-primary',
        }
        return icons.get(self.file_type, 'bi-file-earmark-fill text-secondary')
