from django.db import migrations


def seed_job_market_counts(apps, schema_editor):
    JobMarketCount = apps.get_model('landing', 'JobMarketCount')
    rows = [
        ('Türkiye', '🇹🇷', 99, 'https://www.linkedin.com/jobs/search/?keywords=GRC&location=Turkey'),
        ('Almanya', '🇩🇪', 998, 'https://www.linkedin.com/jobs/search/?keywords=GRC&location=Germany'),
        ('Japonya', '🇯🇵', 287, 'https://www.linkedin.com/jobs/search/?keywords=GRC&location=Japan'),
        ('ABD', '🇺🇸', 17348, 'https://www.linkedin.com/jobs/search/?keywords=GRC&location=United%20States'),
    ]
    for country, flag, count, search_url in rows:
        JobMarketCount.objects.update_or_create(
            country=country,
            defaults={
                'flag': flag,
                'grc': count,
                'search_url': search_url,
                'source_label': 'Piyasa göstergesi',
                'is_demo': True,
            },
        )


def remove_seeded_job_market_counts(apps, schema_editor):
    JobMarketCount = apps.get_model('landing', 'JobMarketCount')
    JobMarketCount.objects.filter(
        country__in=['Türkiye', 'Almanya', 'Japonya', 'ABD'],
        source_label='Piyasa göstergesi',
        is_demo=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('landing', '0006_assessmentsession_lead_discount_expires_at_and_more')]

    operations = [
        migrations.RunPython(seed_job_market_counts, remove_seeded_job_market_counts),
    ]
