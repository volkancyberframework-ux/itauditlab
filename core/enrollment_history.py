"""Recover archived enrollment history from real first-access evidence only."""
from django.db.models import Exists, OuterRef


def restore_access_history(apps, context):
    """Reconstruct archived history only from verified first-access timestamps."""
    Enrollment=apps.get_model('core','Enrollment')
    Evidence=apps.get_model('core','LessonEvidence')
    alias=context.connection.alias
    existing=Enrollment.objects.using(alias).filter(user_id=OuterRef('user_id'),course_id=OuterRef('course_id'))
    missing=Evidence.objects.using(alias).filter(
        first_accessed_at__isnull=False, user__is_staff=False, user__is_superuser=False,
    ).annotate(has_enrollment=Exists(existing)).filter(has_enrollment=False)
    restored=0
    for evidence in missing.iterator(chunk_size=200):
        item,created=Enrollment.objects.using(alias).get_or_create(
            user_id=evidence.user_id,course_id=evidence.course_id,
            defaults={'is_archived':True,'restored_from_access':True,'is_automatic':False},
        )
        if created:
            Enrollment.objects.using(alias).filter(pk=item.pk).update(enrolled_at=evidence.first_accessed_at)
            restored+=1

    return restored
