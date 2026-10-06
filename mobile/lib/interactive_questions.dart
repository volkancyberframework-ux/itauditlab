import 'package:flutter/material.dart';
import 'theme.dart';

class SentenceBuilder extends StatelessWidget {
  final List<dynamic> options;
  final List<String> value;
  final ValueChanged<List<String>> onChanged;
  final bool enabled;
  const SentenceBuilder({
    super.key,
    required this.options,
    required this.value,
    required this.onChanged,
    required this.enabled,
  });
  String label(String id) => options.firstWhere((o) => o['id'] == id)['text'];
  void add(String id) {
    if (enabled && !value.contains(id)) onChanged([...value, id]);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'RİSK CÜMLEN',
          style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1),
        ),
        const SizedBox(height: 10),
        DragTarget<String>(
          onWillAcceptWithDetails: (d) => enabled && !value.contains(d.data),
          onAcceptWithDetails: (d) => add(d.data),
          builder: (_, candidate, _) => AnimatedContainer(
            duration: const Duration(milliseconds: 160),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: candidate.isNotEmpty
                  ? AppColors.teal.withValues(alpha: .2)
                  : scheme.surface,
              borderRadius: BorderRadius.circular(22),
              border: Border.all(
                color: candidate.isNotEmpty
                    ? AppColors.teal
                    : scheme.outlineVariant,
                width: 2,
              ),
            ),
            child: value.isEmpty
                ? const SizedBox(
                    height: 100,
                    child: Center(
                      child: Text(
                        'Parçaları buraya taşı\nveya aşağıdaki kartlara dokun.',
                        textAlign: TextAlign.center,
                        style: TextStyle(height: 1.6),
                      ),
                    ),
                  )
                : Column(
                    children: [
                      ReorderableListView.builder(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        buildDefaultDragHandles: false,
                        itemCount: value.length,
                        onReorderItem: (oldIndex, newIndex) {
                          if (!enabled) return;
                          final items = [...value];
                          items.insert(newIndex, items.removeAt(oldIndex));
                          onChanged(items);
                        },
                        itemBuilder: (_, i) => Container(
                          key: ValueKey(value[i]),
                          margin: const EdgeInsets.only(bottom: 8),
                          decoration: BoxDecoration(
                            color: AppColors.teal.withValues(alpha: .12),
                            borderRadius: BorderRadius.circular(14),
                          ),
                          child: Row(
                            children: [
                              if (enabled)
                                ReorderableDragStartListener(
                                  index: i,
                                  child: const Padding(
                                    padding: EdgeInsets.all(10),
                                    child: Icon(
                                      Icons.drag_indicator_rounded,
                                      color: AppColors.teal,
                                    ),
                                  ),
                                ),
                              Expanded(
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 12,
                                  ),
                                  child: Text(
                                    '${i + 1}. ${label(value[i])}',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w700,
                                      height: 1.4,
                                    ),
                                  ),
                                ),
                              ),
                              IconButton(
                                tooltip: 'Parçayı geri al',
                                onPressed: enabled
                                    ? () {
                                        final items = [...value]..removeAt(i);
                                        onChanged(items);
                                      }
                                    : null,
                                icon: const Icon(Icons.close_rounded, size: 18),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const Divider(),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          value.map(label).join(' '),
                          style: TextStyle(
                            color: scheme.onSurfaceVariant,
                            height: 1.5,
                          ),
                        ),
                      ),
                    ],
                  ),
          ),
        ),
        const SizedBox(height: 20),
        const Text(
          'CÜMLE PARÇALARI',
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w900,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Kartın tamamına dokunarak ekle. Taşımak için sağdaki tutamacı sürükle.',
          style: TextStyle(fontSize: 12, height: 1.4),
        ),
        const SizedBox(height: 12),
        for (final option in options.where((o) => !value.contains(o['id'])))
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: _MovableCard(
              id: option['id'],
              label: option['text'],
              enabled: enabled,
              onTap: () => add(option['id']),
            ),
          ),
      ],
    );
  }
}

class DragRiskQuestion extends StatefulWidget {
  final List<dynamic> options;
  final List<String> value;
  final ValueChanged<List<String>> onChanged;
  final bool enabled;
  const DragRiskQuestion({
    super.key,
    required this.options,
    required this.value,
    required this.onChanged,
    required this.enabled,
  });
  @override
  State<DragRiskQuestion> createState() => _DragRiskQuestionState();
}

class _DragRiskQuestionState extends State<DragRiskQuestion> {
  final pages = PageController(viewportFraction: .92);
  int page = 0;
  @override
  void dispose() {
    pages.dispose();
    super.dispose();
  }

  void select(String id) {
    if (widget.enabled) widget.onChanged([id]);
  }

  double cardHeight(BuildContext context, double width) {
    double height = 220;
    for (final option in widget.options) {
      final painter = TextPainter(
        text: TextSpan(
          text: option['text'],
          style: DefaultTextStyle.of(context).style.merge(
            const TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              height: 1.45,
            ),
          ),
        ),
        textDirection: Directionality.of(context),
        textScaler: MediaQuery.textScalerOf(context),
      )..layout(maxWidth: (width * .92 - 94).clamp(60.0, double.infinity));
      if (painter.height + 80 > height) height = painter.height + 80;
      painter.dispose();
    }
    return height;
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DragTarget<String>(
          onWillAcceptWithDetails: (d) =>
              widget.enabled && widget.options.any((o) => o['id'] == d.data),
          onAcceptWithDetails: (d) => select(d.data),
          builder: (_, candidate, _) => Container(
            width: double.infinity,
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              color: AppColors.teal.withValues(
                alpha: candidate.isNotEmpty ? .22 : .10,
              ),
              borderRadius: BorderRadius.circular(22),
              border: Border.all(color: AppColors.teal, width: 2),
            ),
            child: Column(
              children: [
                const Icon(
                  Icons.shield_rounded,
                  color: AppColors.teal,
                  size: 32,
                ),
                const SizedBox(height: 10),
                Text(
                  widget.value.isEmpty
                      ? 'Riski buraya taşı'
                      : widget.options.firstWhere(
                          (o) => o['id'] == widget.value.first,
                        )['text'],
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontWeight: FontWeight.w800,
                    height: 1.5,
                  ),
                ),
                if (widget.value.isNotEmpty)
                  TextButton(
                    onPressed: widget.enabled
                        ? () => widget.onChanged([])
                        : null,
                    child: const Text('Seçimi değiştir'),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Kartı kaydır veya okları kullan. Seçmek için karta dokun; taşımak için sağdaki tutamacı sürükle.',
          style: TextStyle(fontSize: 12, height: 1.5),
        ),
        const SizedBox(height: 14),
        LayoutBuilder(
          builder: (context, constraints) => SizedBox(
            height: cardHeight(context, constraints.maxWidth),
            child: PageView.builder(
              controller: pages,
              physics: const PageScrollPhysics(),
              itemCount: widget.options.length,
              onPageChanged: (v) => setState(() => page = v),
              itemBuilder: (_, i) => Padding(
                padding: const EdgeInsets.only(right: 10),
                child: _MovableCard(
                  id: widget.options[i]['id'],
                  label: widget.options[i]['text'],
                  enabled: widget.enabled,
                  onTap: () => select(widget.options[i]['id']),
                  selected: widget.value.contains(widget.options[i]['id']),
                  actionLabel: 'Riski seç',
                ),
              ),
            ),
          ),
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            IconButton(
              tooltip: 'Önceki kart',
              constraints: const BoxConstraints(minWidth: 56, minHeight: 56),
              iconSize: 32,
              onPressed: page > 0
                  ? () => pages.previousPage(
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeOut,
                    )
                  : null,
              icon: const Icon(Icons.chevron_left_rounded),
            ),
            Text(
              '${page + 1} / ${widget.options.length}',
              style: TextStyle(
                color: scheme.onSurfaceVariant,
                fontWeight: FontWeight.w800,
              ),
            ),
            IconButton(
              tooltip: 'Sonraki kart',
              constraints: const BoxConstraints(minWidth: 56, minHeight: 56),
              iconSize: 32,
              onPressed: page < widget.options.length - 1
                  ? () => pages.nextPage(
                      duration: const Duration(milliseconds: 200),
                      curve: Curves.easeOut,
                    )
                  : null,
              icon: const Icon(Icons.chevron_right_rounded),
            ),
          ],
        ),
      ],
    );
  }
}

class _MovableCard extends StatelessWidget {
  final String id, label, actionLabel;
  final bool enabled, selected;
  final VoidCallback onTap;
  const _MovableCard({
    required this.id,
    required this.label,
    required this.enabled,
    required this.onTap,
    this.selected = false,
    this.actionLabel = 'Cümleme ekle',
  });

  Widget card(BuildContext context, {bool floating = false}) => Material(
    color: Theme.of(context).colorScheme.surface,
    elevation: floating ? 8 : 0,
    borderRadius: BorderRadius.circular(18),
    child: InkWell(
      onTap: enabled && !floating ? onTap : null,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        constraints: const BoxConstraints(minHeight: 88),
        padding: const EdgeInsets.fromLTRB(16, 16, 8, 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: selected
                ? AppColors.teal
                : Theme.of(context).colorScheme.outlineVariant,
            width: 2,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      height: 1.45,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Icon(
                        selected
                            ? Icons.check_circle_rounded
                            : Icons.touch_app_rounded,
                        size: 18,
                        color: AppColors.teal,
                      ),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          selected ? 'Seçildi' : actionLabel,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.primary,
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            if (enabled && !floating)
              Draggable<String>(
                data: id,
                affinity: Axis.vertical,
                dragAnchorStrategy: pointerDragAnchorStrategy,
                feedback: SizedBox(
                  width: MediaQuery.sizeOf(context).width - 64,
                  child: card(context, floating: true),
                ),
                childWhenDragging: const SizedBox(width: 52, height: 64),
                child: Tooltip(
                  message: 'Taşı',
                  child: Container(
                    width: 52,
                    height: 64,
                    decoration: BoxDecoration(
                      color: AppColors.teal.withValues(alpha: .12),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: const Icon(
                      Icons.drag_indicator_rounded,
                      color: AppColors.teal,
                      size: 30,
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    ),
  );
  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    selected: selected,
    label: label,
    child: card(context),
  );
}
