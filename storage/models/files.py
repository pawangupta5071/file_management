from django.conf import settings
from django.db import models

class File(models.Model):
    id = models.AutoField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,db_column="owner_id")
    name = models.TextField()
    size = models.BigIntegerField()
    mime_type = models.TextField()
    storage_key = models.TextField(unique=True)
    status = models.TextField()
    fingerprint = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "files"
        indexes = [
            models.Index(fields=["owner", "fingerprint"],name="ix_files_owner_fingerprint"),
            models.Index(fields=["updated_at"],name="ix_files_updated_at"),
        ]
    
    def __str__(self):
        return self.name