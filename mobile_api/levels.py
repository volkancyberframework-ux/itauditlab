from .models import LevelSettings, LevelReward, UserLevelReward


def level_data(total_xp, user=None):
    settings = LevelSettings.objects.filter(pk=1).first()
    step = max(1, settings.xp_per_level if settings else 100)
    level = max(0, total_xp) // step
    rewards = list(LevelReward.objects.filter(published=True))
    claims = {}
    if user is not None:
        for reward in rewards:
            if level >= reward.level:
                UserLevelReward.objects.get_or_create(user=user, reward=reward)
        claims = {claim.reward_id: claim for claim in UserLevelReward.objects.filter(user=user, reward__in=rewards)}
    return {
        'level': level,
        'xp_per_level': step,
        'level_progress': (max(0, total_xp) % step) / step,
        'next_level_xp': (level + 1) * step,
        'rewards': [
            {
                'id': reward.pk, 'level': reward.level, 'title': reward.title,
                'description': reward.description, 'kind': reward.kind,
                'required_xp': reward.level * step,
                'remaining_xp': max(0, reward.level * step - total_xp),
                'unlocked': reward.pk in claims if user is not None else level >= reward.level,
                'delivered': bool(claims.get(reward.pk) and claims[reward.pk].delivered_at),
            }
            for reward in rewards
        ],
    }
