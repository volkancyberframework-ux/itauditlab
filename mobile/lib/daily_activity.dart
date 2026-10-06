import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'theme.dart';

class DailyActivityChart extends StatefulWidget {
  final Map<String, dynamic> activity;
  const DailyActivityChart({super.key, required this.activity});
  @override
  State<DailyActivityChart> createState() => _DailyActivityChartState();
}

class _DailyActivityChartState extends State<DailyActivityChart> {
  int count = 7;
  int? selected;

  @override
  Widget build(BuildContext context) {
    final all = (widget.activity['days'] as List?) ?? [];
    final days = all.skip(math.max(0, all.length - count)).toList();
    final peak = days.fold<int>(
      1,
      (value, day) => math.max(value, (day['tasks'] as num).toInt()),
    );
    final chosen = selected != null && selected! < days.length
        ? days[selected!]
        : null;
    final color = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Her gün bir adım',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
            ),
            const SizedBox(height: 8),
            Text(
              '${widget.activity['streak'] ?? 0} günlük seri • Son 28 günde ${widget.activity['active_days'] ?? 0} aktif gün',
              style: TextStyle(color: color.onSurfaceVariant),
            ),
            const SizedBox(height: 18),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 7, label: Text('7 gün')),
                ButtonSegment(value: 28, label: Text('28 gün')),
              ],
              selected: {count},
              onSelectionChanged: (values) => setState(() {
                count = values.first;
                selected = null;
              }),
            ),
            const SizedBox(height: 26),
            if (days.isEmpty)
              const Text(
                'Günlük takip verileri şu anda yüklenemedi. Ekranı yenileyebilirsin.',
              )
            else
              SizedBox(
                height: 150,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    for (var i = 0; i < days.length; i++)
                      Expanded(
                        child: Semantics(
                          label:
                              '${days[i]['date']}: ${days[i]['tasks']} görev, ${days[i]['xp']} XP',
                          button: true,
                          child: GestureDetector(
                            behavior: HitTestBehavior.opaque,
                            onTap: () => setState(() => selected = i),
                            child: Padding(
                              padding: EdgeInsets.symmetric(
                                horizontal: count == 7 ? 4 : 1,
                              ),
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.end,
                                children: [
                                  if (count == 7)
                                    Text(
                                      '${days[i]['tasks']}',
                                      style: const TextStyle(
                                        fontWeight: FontWeight.w700,
                                        fontSize: 11,
                                      ),
                                    ),
                                  const SizedBox(height: 6),
                                  Container(
                                    height: math.max(
                                      5.0,
                                      (days[i]['tasks'] as num).toDouble() /
                                          peak *
                                          104,
                                    ),
                                    decoration: BoxDecoration(
                                      color: selected == i
                                          ? AppColors.gold
                                          : days[i]['tasks'] == 0
                                          ? color.outlineVariant
                                          : AppColors.teal,
                                      borderRadius: BorderRadius.circular(5),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    count == 7 || i % 7 == 0
                                        ? '${DateTime.parse(days[i]['date']).day}'
                                        : '',
                                    style: TextStyle(
                                      fontSize: 10,
                                      color: color.onSurfaceVariant,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            const SizedBox(height: 16),
            Text(
              chosen == null
                  ? 'Bugün ${widget.activity['today_tasks'] ?? 0} görev yaptın. Bir güne dokun, detayını gör.'
                  : '${chosen['date']} • ${chosen['tasks']} görev • ${chosen['xp']} XP',
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }
}
