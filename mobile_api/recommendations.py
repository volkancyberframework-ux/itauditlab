from typing import Protocol


class RecommendationProvider(Protocol):
    def recommend(
        self, questions, *, level: str, minutes: int, goal: str
    ) -> list[int]: ...


class RuleRecommendationProvider:
    def recommend(self, questions, *, level, minutes, goal):
        # Stable ranking: goal relevance, content order, primary key. Future AI can implement the same interface.
        candidates = list(questions.filter(difficulty=level))
        candidates.sort(key=lambda q: (goal not in q.goals, q.order, q.pk))
        return [q.pk for q in candidates[: minutes * 2]]
