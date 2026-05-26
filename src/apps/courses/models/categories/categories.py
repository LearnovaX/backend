from django.db import models

from src.apps.common.models import BaseModel


class Category(BaseModel):
    name = models.CharField(max_length=100)
    parent_category = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="subcategories", null=True, blank=True
    )

    def __str__(self):
        return self.name

    def get_all_subcategories(self, visited=None):
        if visited is None:
            visited = set()

        if self.id in visited:
            return []
        visited.add(self.id)
        subcategories = list(self.subcategories.all())

        for subcategory in subcategories:
            subcategories.extend(subcategory.get_all_subcategories(visited.copy()))
        return subcategories

    class Meta:
        db_table = "Categories"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
