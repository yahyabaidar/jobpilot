from django.db import transaction
from django.utils import timezone

from .models import Application, StatusChange


def create_or_get_application(user, job_offer) -> tuple[Application, bool]:
    application, created = Application.objects.get_or_create(
        user=user,
        job_offer=job_offer,
        defaults={"status": Application.Status.SENT},
    )
    if created:
        StatusChange.objects.create(application=application, status=application.status)
    return application, created


def move_application(application: Application, new_status: str, ordered_ids: list[int]) -> None:
    """Update the moved card's status/position and re-sequence its target column."""
    with transaction.atomic():
        status_changed = application.status != new_status
        if status_changed:
            application.status = new_status
            application.status_changed_at = timezone.now()
            application.save(update_fields=["status", "status_changed_at"])
            StatusChange.objects.create(application=application, status=new_status)

        column_applications = {
            app.pk: app
            for app in Application.objects.filter(pk__in=ordered_ids, user=application.user)
        }
        to_update = []
        for index, app_id in enumerate(ordered_ids):
            app_obj = column_applications.get(app_id)
            if app_obj is None:
                continue
            if app_obj.position != index:
                app_obj.position = index
                to_update.append(app_obj)
        if to_update:
            Application.objects.bulk_update(to_update, ["position"])
