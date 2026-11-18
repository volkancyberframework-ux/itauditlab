# Enrollment history and notification consistency

Student removal from the learning list archives Enrollment instead of deleting it. The active dashboard, direct video access and meeting permission exclude archived rows; student monitoring retains genuine earlier completion. Re-enrollment reactivates the same row, using the existing access checks.

Admin inlines show the enrollment time, archive flag and read-only `restored_from_access` marker. A restored time is the verified first course access, not a claim about the original enrollment timestamp.

Telegram enrollment notifications run on transaction commit and re-read the saved row. Rolled-back, deleted, archived and automatic access rows do not send a student enrollment notification. A student converting automatic access or reactivating an archive sends one notification with enrollment/user/course identifiers. Network failure does not roll back enrollment. Physical deletions are logged after commit.

Migration 0039 adds the flags and leaves safe PostgreSQL defaults for old workers during deployment. It does not reconstruct data before the new code is live.

After the new web release is live:

```sh
python manage.py restore_enrollment_history
python manage.py restore_enrollment_history --apply
```

The first command is read-only. The second transactionally restores only missing, non-staff history supported by a real `LessonEvidence.first_accessed_at`, as archived records. It is idempotent, does not change existing enrollments, grant new access, or send Telegram messages. Missing histories without real access evidence are not invented.
