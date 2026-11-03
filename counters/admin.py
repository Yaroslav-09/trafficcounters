from django.contrib import admin

from .forms import CounterEventAdminForm
from .models import Client, Counter, CounterEvent, CounterInspection, CounterType


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'email', 'phone', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'contact_person', 'email', 'phone')


@admin.register(CounterType)
class CounterTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


class CounterEventInline(admin.TabularInline):
    model = CounterEvent
    form = CounterEventAdminForm
    extra = 0
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ('name', 'client', 'counter_type', 'status', 'address', 'updated_at')
    list_filter = ('status', 'client', 'counter_type')
    search_fields = ('name', 'address', 'client__name', 'counter_type__name')
    inlines = [CounterEventInline]


@admin.register(CounterEvent)
class CounterEventAdmin(admin.ModelAdmin):
    form = CounterEventAdminForm
    list_display = ('counter', 'status', 'actor', 'created_at')
    list_filter = ('status',)
    search_fields = ('counter__name', 'actor__username', 'actor__first_name', 'actor__last_name', 'note')
    ordering = ('-created_at',)


@admin.register(CounterInspection)
class CounterInspectionAdmin(admin.ModelAdmin):
    list_display = ('counter', 'inspected_at', 'result', 'next_inspection_at', 'actor')
    list_filter = ('result', 'inspected_at')
    search_fields = ('counter__name', 'counter__client__name', 'note', 'actor__username')
    readonly_fields = ('created_at',)
    ordering = ('-inspected_at', '-created_at')
    readonly_fields = ('created_at',)
