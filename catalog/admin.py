from django.contrib import admin
from .models import Category, Product, ProductVariant


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon_emoji", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "unit_type", "is_organic", "is_active")
    list_filter = ("category", "unit_type", "is_organic", "is_active")
    search_fields = ("name",)
    inlines = [ProductVariantInline]
