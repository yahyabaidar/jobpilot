from django.contrib import admin

from .models import CVDocument, Education, Experience, Profile, SearchPreference, Skill


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "city", "years_of_experience", "updated_at"]
    search_fields = ["user__email", "title", "city"]
    inlines = [SkillInline, ExperienceInline, EducationInline]


@admin.register(CVDocument)
class CVDocumentAdmin(admin.ModelAdmin):
    list_display = ["original_name", "user", "status", "uploaded_at"]
    list_filter = ["status"]
    search_fields = ["original_name", "user__email"]


@admin.register(SearchPreference)
class SearchPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "contract_types", "countries", "remote_ok", "updated_at"]
    search_fields = ["user__email"]
