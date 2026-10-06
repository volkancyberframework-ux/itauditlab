import 'package:flutter/material.dart';
import 'theme.dart';

/// A deliberately small, safe formatting subset for admin-authored lesson text.
class LessonText extends StatelessWidget {
  final String text;
  const LessonText(this.text, {super.key});
  @override
  Widget build(BuildContext context) {
    final spans = <InlineSpan>[];
    final pattern = RegExp(r'\*\*\*([^*]+)\*\*\*|\*\*([^*]+)\*\*|\*([^*]+)\*');
    var cursor = 0;
    for (final match in pattern.allMatches(text)) {
      spans.add(TextSpan(text: text.substring(cursor, match.start)));
      spans.add(
        TextSpan(
          text: match.group(1) ?? match.group(2) ?? match.group(3),
          style: TextStyle(
            fontWeight: match.group(3) == null ? FontWeight.w900 : null,
            fontStyle: match.group(2) == null ? FontStyle.italic : null,
          ),
        ),
      );
      cursor = match.end;
    }
    spans.add(TextSpan(text: text.substring(cursor)));
    return Text.rich(
      TextSpan(children: spans),
      style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.7),
    );
  }
}

class InformationCard extends StatefulWidget {
  final Map<String, dynamic> question;
  final String pathTitle;
  final int answered;
  final int total;
  final Future<void> Function() onContinue;
  const InformationCard({
    super.key,
    required this.question,
    required this.pathTitle,
    required this.answered,
    required this.total,
    required this.onContinue,
  });
  @override
  State<InformationCard> createState() => _InformationCardState();
}

class _InformationCardState extends State<InformationCard> {
  final controller = PageController();
  final revealed = <int>{};
  int page = 0;
  bool busy = false;
  String? error;
  List<dynamic> get pages =>
      (widget.question['card_pages'] as List?)?.isNotEmpty == true
      ? widget.question['card_pages']
      : [
          {
            'title': widget.question['prompt'],
            'body': widget.question['context'],
          },
        ];
  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  Future<void> finish() async {
    if (busy) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await widget.onContinue();
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: Text(widget.pathTitle, style: const TextStyle(fontSize: 16)),
    ),
    body: SafeArea(
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 8),
            child: Column(
              children: [
                Row(
                  children: [
                    const Icon(
                      Icons.auto_stories_rounded,
                      color: AppColors.teal,
                    ),
                    const SizedBox(width: 8),
                    const Text(
                      'BİLGİ KARTI',
                      style: TextStyle(fontWeight: FontWeight.w900),
                    ),
                    const Spacer(),
                    Text('${widget.answered + 1} / ${widget.total}'),
                  ],
                ),
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: widget.answered / widget.total,
                  minHeight: 8,
                  borderRadius: BorderRadius.circular(12),
                ),
              ],
            ),
          ),
          Expanded(
            child: PageView.builder(
              controller: controller,
              itemCount: pages.length + 1,
              onPageChanged: (index) {
                setState(() => page = index);
                if (index == pages.length) finish();
              },
              itemBuilder: (context, index) {
                if (index == pages.length) {
                  return Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.check_circle_rounded,
                            color: AppColors.teal,
                            size: 64,
                          ),
                          const SizedBox(height: 24),
                          const Text(
                            'Bilgiyi öğrendin. Sıradaki adıma geçelim!',
                          ),
                          const SizedBox(height: 24),
                          if (error != null) Text(error!),
                          PrimaryButton(
                            label: 'Devam et',
                            busy: busy,
                            onPressed: finish,
                          ),
                        ],
                      ),
                    ),
                  );
                }
                final data = pages[index] as Map;
                final color = [
                  AppColors.teal,
                  AppColors.gold,
                  const Color(0xFF8D75D9),
                ][index % 3];
                return SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: .13),
                      borderRadius: BorderRadius.circular(28),
                      border: Border.all(
                        color: color.withValues(alpha: .5),
                        width: 2,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          [
                            Icons.lightbulb_rounded,
                            Icons.explore_rounded,
                            Icons.auto_awesome_rounded,
                          ][index % 3],
                          color: color,
                          size: 48,
                        ),
                        const SizedBox(height: 24),
                        Text(
                          data['title'] ?? '',
                          style: Theme.of(context).textTheme.headlineSmall
                              ?.copyWith(fontWeight: FontWeight.w900),
                        ),
                        const SizedBox(height: 24),
                        LessonText(data['body'] ?? ''),
                        if ((data['reveal'] ?? '').toString().isNotEmpty) ...[
                          const SizedBox(height: 24),
                          OutlinedButton.icon(
                            onPressed: () => setState(() {
                              if (!revealed.add(index)) revealed.remove(index);
                            }),
                            icon: Icon(
                              revealed.contains(index)
                                  ? Icons.visibility_off_outlined
                                  : Icons.touch_app_rounded,
                            ),
                            label: Text(
                              revealed.contains(index)
                                  ? 'Açıklamayı gizle'
                                  : 'Biraz daha öğren',
                            ),
                          ),
                          AnimatedSize(
                            duration: const Duration(milliseconds: 240),
                            child: revealed.contains(index)
                                ? Padding(
                                    padding: const EdgeInsets.only(top: 16),
                                    child: LessonText(data['reveal']),
                                  )
                                : const SizedBox.shrink(),
                          ),
                        ],
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          if (page < pages.length)
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 0, 24, 20),
              child: Column(
                children: [
                  Text(
                    '${page + 1} / ${pages.length} sayfa • sola kaydır →',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 12),
                  PrimaryButton(
                    label: page == pages.length - 1
                        ? 'Öğrendim, devam et'
                        : 'Sonraki sayfa',
                    onPressed: () => controller.nextPage(
                      duration: const Duration(milliseconds: 280),
                      curve: Curves.easeOut,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    ),
  );
}
