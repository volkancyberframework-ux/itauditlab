import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// One provider is shared by the preview and viewer, including authenticated headers.
class QuestionImagePreview extends StatefulWidget {
  final ImageProvider imageProvider;
  const QuestionImagePreview({super.key, required this.imageProvider});
  @override
  State<QuestionImagePreview> createState() => _QuestionImagePreviewState();
}

class _QuestionImagePreviewState extends State<QuestionImagePreview> {
  int revision = 0;
  Widget imageError(BuildContext context, Object error, StackTrace? stack) =>
      Column(
        children: [
          const Text('Görsel yüklenemedi. Bağlantını kontrol et.'),
          TextButton(
            onPressed: () async {
              await widget.imageProvider.evict();
              if (mounted) setState(() => revision++);
            },
            child: const Text('Yeniden dene'),
          ),
        ],
      );
  @override
  Widget build(BuildContext context) => Column(
    children: [
      Semantics(
        button: true,
        label: 'Ekran görüntüsünü büyüt',
        child: InkWell(
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute<void>(
              fullscreenDialog: true,
              builder: (_) =>
                  FullscreenImageViewer(imageProvider: widget.imageProvider),
            ),
          ),
          child: Image(
            key: ValueKey(revision),
            image: widget.imageProvider,
            height: 220,
            width: double.infinity,
            fit: BoxFit.contain,
            filterQuality: FilterQuality.high,
            errorBuilder: imageError,
            loadingBuilder: (_, child, progress) => progress == null
                ? child
                : const SizedBox(
                    height: 220,
                    child: Center(child: CircularProgressIndicator()),
                  ),
          ),
        ),
      ),
      const Padding(
        padding: EdgeInsets.symmetric(vertical: 10),
        child: Text(
          '🔍 Ekran görüntüsünü büyütmek için tıkla',
          textAlign: TextAlign.center,
        ),
      ),
    ],
  );
}

class FullscreenImageViewer extends StatefulWidget {
  final ImageProvider imageProvider;
  const FullscreenImageViewer({super.key, required this.imageProvider});
  @override
  State<FullscreenImageViewer> createState() => _FullscreenImageViewerState();
}

class _FullscreenImageViewerState extends State<FullscreenImageViewer> {
  final controller = TransformationController();
  Offset doubleTapPosition = Offset.zero;
  int revision = 0;
  void fit() => controller.value = Matrix4.identity();
  void zoom(double factor, Offset anchor) {
    final previous = controller.value.getMaxScaleOnAxis();
    final next = (previous * factor).clamp(1.0, 16.0);
    final scene = controller.toScene(anchor);
    controller.value = Matrix4.identity()
      ..translateByDouble(
        anchor.dx - scene.dx * next,
        anchor.dy - scene.dy * next,
        0,
        1,
      )
      ..scaleByDouble(next, next, 1, 1);
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Shortcuts(
    shortcuts: const {
      SingleActivator(LogicalKeyboardKey.escape): DismissIntent(),
    },
    child: Actions(
      actions: {
        DismissIntent: CallbackAction<DismissIntent>(
          onInvoke: (_) {
            Navigator.of(context).maybePop();
            return null;
          },
        ),
      },
      child: Focus(
        autofocus: true,
        child: Scaffold(
          backgroundColor: const Color(0xff071421),
          appBar: AppBar(
            title: const Text('Ekran görüntüsü'),
            actions: [
              IconButton(
                tooltip: 'Ekrana sığdır',
                onPressed: fit,
                icon: const Icon(Icons.fit_screen),
              ),
              IconButton(
                tooltip: 'Zoom sıfırla',
                onPressed: fit,
                icon: const Icon(Icons.restart_alt),
              ),
              IconButton(
                tooltip: 'Kapat',
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.close),
              ),
            ],
          ),
          body: SafeArea(
            child: LayoutBuilder(
              builder: (context, size) {
                final center = Offset(size.maxWidth / 2, size.maxHeight / 2);
                return Stack(
                  children: [
                    Positioned.fill(
                      child: GestureDetector(
                        onDoubleTapDown: (details) =>
                            doubleTapPosition = details.localPosition,
                        onDoubleTap: () =>
                            controller.value.getMaxScaleOnAxis() > 1.05
                            ? fit()
                            : zoom(2, doubleTapPosition),
                        child: InteractiveViewer(
                          transformationController: controller,
                          minScale: 1,
                          maxScale: 16,
                          child: SizedBox(
                            width: size.maxWidth,
                            height: size.maxHeight,
                            child: Image(
                              key: ValueKey(revision),
                              image: widget.imageProvider,
                              fit: BoxFit.contain,
                              filterQuality: FilterQuality.high,
                              errorBuilder: (_, _, _) => Center(
                                child: TextButton(
                                  onPressed: () async {
                                    await widget.imageProvider.evict();
                                    if (mounted) setState(() => revision++);
                                  },
                                  child: const Text(
                                    'Görsel yüklenemedi · Yeniden dene',
                                  ),
                                ),
                              ),
                              loadingBuilder: (_, child, progress) =>
                                  progress == null
                                  ? child
                                  : const Center(
                                      child: CircularProgressIndicator(),
                                    ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      bottom: 12,
                      right: 12,
                      child: Row(
                        children: [
                          IconButton.filled(
                            tooltip: 'Uzaklaştır',
                            onPressed: () => zoom(.5, center),
                            icon: const Icon(Icons.remove),
                          ),
                          const SizedBox(width: 8),
                          IconButton.filled(
                            tooltip: 'Yakınlaştır',
                            onPressed: () => zoom(2, center),
                            icon: const Icon(Icons.add),
                          ),
                        ],
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ),
      ),
    ),
  );
}
