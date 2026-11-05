from django.contrib import admin

from .models import Office, Visit, Visitor


@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ('office_name', 'location')
    search_fields = ('office_name', 'location')
    ordering = ('office_name',)


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'visitor_type_display', 'contact_number')
    list_filter = ('visitor_type',)
    search_fields = ('first_name', 'last_name', 'contact_number', 'visitor_type_other')


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('visitor', 'office', 'time_in', 'time_out', 'status', 'recorded_by')
    list_filter = ('status', 'office', 'time_in', 'visitor__visitor_type')
    search_fields = ('visitor__first_name', 'visitor__last_name', 'purpose', 'person_to_visit')
    date_hierarchy = 'time_in'
    list_select_related = ('visitor', 'office', 'recorded_by')
    readonly_fields = ('visitor', 'office', 'recorded_by', 'purpose', 'person_to_visit', 'time_in', 'time_out', 'status')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.site_header = 'VSLog Administration'
admin.site.site_title = 'VSLog'
admin.site.index_title = 'School visitor system management'
