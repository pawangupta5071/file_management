from django.conf import settings
from django.db import models
from storage.models.files import File

class FileShare(models.Model):
    pk = models.CompositePrimaryKey("user", "file")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.ForeignKey(File, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "file_shares"

    def __str__(self):
        return f"{self.user.email} - {self.file.name}"