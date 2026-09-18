from django.contrib import admin

from .models import Counter, CounterEvent


class CounterEventInline(admin.TabularInline):
    model = CounterEvent
    extra = 0
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'address', 'latitude', 'longitude', 'updated_at')
    list_filter = ('status',)
    search_fields = ('name', 'address')
    inlines = [CounterEventInline]


@admin.register(CounterEvent)
class CounterEventAdmin(admin.ModelAdmin):
    list_display = ('counter', 'status', 'actor', 'created_at')
    list_filter = ('status',)
    search_fields = ('counter__name', 'actor__username', 'actor__first_name', 'actor__last_name', 'note')
    ordering = ('-created_at',)
