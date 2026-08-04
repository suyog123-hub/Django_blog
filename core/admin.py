from django.contrib import admin

from .models import Blog


class BlogAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "created_date", "is_approved")
    list_filter = ("is_approved", "author")
    search_fields = ("title", "content")
    actions = ("approve_blogs",)

    def approve_blogs(self, request, queryset):
        queryset.update(is_approved=True)

    approve_blogs.short_description = "Approve selected blogs"


admin.site.register(Blog, BlogAdmin)
