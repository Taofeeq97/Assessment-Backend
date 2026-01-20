from django.db import models
from django.utils import timezone
from base.managers import ActiveManager, DeletedManager


class BaseModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = ActiveManager()
    all_objects = models.Manager()
    active_objects = ActiveManager()
    deleted_objects = DeletedManager()

    class Meta:
        abstract = True
        ordering = ['-created_at', ]

    def soft_delete(self):
        if hasattr(self, 'is_active'):
            try:
                self.is_active = False
            except AttributeError:
                pass
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def delete(self):
        return self.soft_delete()

    def force_delete(self):
        return super().delete()