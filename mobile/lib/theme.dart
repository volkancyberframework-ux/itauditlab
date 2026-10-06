import 'package:flutter/material.dart';

class AppColors {
  static const gold = Color(0xFFF6C453);
  static const teal = Color(0xFF19B69A);
  static const primary = Color(0xFF19B69A);
  static const ink = Color(0xFF142C46);
  static const background = Color(0xFFF7F8FC);
}

class AppSpacing {
  static const double page = 24;
}

class AppRadius {
  static const double card = 24;
}

class AppTheme {
  static ThemeData create(Brightness brightness) => ThemeData(
    useMaterial3: true,
    brightness: brightness,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.primary,
      brightness: brightness,
      surface: brightness == Brightness.light
          ? Colors.white
          : const Color(0xFF182B42),
    ),
    scaffoldBackgroundColor: brightness == Brightness.light
        ? AppColors.background
        : const Color(0xFF0D1C30),
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      backgroundColor: Colors.transparent,
      elevation: 0,
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: brightness == Brightness.light
          ? Colors.white
          : const Color(0xFF182B42),
      indicatorColor: AppColors.teal.withValues(alpha: .18),
      labelTextStyle: WidgetStateProperty.all(
        const TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
      ),
    ),
    progressIndicatorTheme: ProgressIndicatorThemeData(
      color: AppColors.teal,
      linearTrackColor: AppColors.teal.withValues(alpha: .12),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      contentPadding: const EdgeInsets.all(20),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFFCCD6E1), width: 2),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(54),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
    ),
  );
}

class PrimaryButton extends StatefulWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool busy;
  const PrimaryButton({
    super.key,
    required this.label,
    this.onPressed,
    this.busy = false,
  });
  @override
  State<PrimaryButton> createState() => _PrimaryButtonState();
}

class _PrimaryButtonState extends State<PrimaryButton> {
  bool pressed = false;
  @override
  Widget build(BuildContext context) {
    final enabled = widget.onPressed != null && !widget.busy;
    return Padding(
      padding: const EdgeInsets.only(bottom: 5),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 90),
        transform: Matrix4.translationValues(0, pressed && enabled ? 4 : 0, 0),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          boxShadow: [
            BoxShadow(
              color: enabled
                  ? const Color(0xFF0B806D)
                  : Theme.of(context).colorScheme.outlineVariant,
              offset: Offset(0, pressed && enabled ? 1 : 5),
            ),
          ],
        ),
        child: Listener(
          onPointerDown: (_) => setState(() => pressed = true),
          onPointerUp: (_) => setState(() => pressed = false),
          onPointerCancel: (_) => setState(() => pressed = false),
          child: FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.teal,
              foregroundColor: AppColors.ink,
            ),
            onPressed: enabled ? widget.onPressed : null,
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: widget.busy
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(widget.label),
            ),
          ),
        ),
      ),
    );
  }
}

class ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback retry;
  const ErrorState({super.key, required this.message, required this.retry});
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.wifi_off_rounded, size: 40),
          const SizedBox(height: 20),
          Text(message, textAlign: TextAlign.center),
          const SizedBox(height: 20),
          PrimaryButton(label: 'Tekrar dene', onPressed: retry),
        ],
      ),
    ),
  );
}

class AnswerOption extends StatelessWidget {
  final String label;
  final String marker;
  final bool selected;
  final VoidCallback? onTap;
  const AnswerOption({
    super.key,
    required this.label,
    required this.marker,
    required this.selected,
    required this.onTap,
  });
  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Semantics(
      selected: selected,
      button: true,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        decoration: BoxDecoration(
          color: selected
              ? colors.primaryContainer
              : colors.surfaceContainerLow,
          boxShadow: [
            BoxShadow(
              color: selected
                  ? AppColors.teal.withValues(alpha: .35)
                  : colors.outlineVariant,
              offset: const Offset(0, 4),
            ),
          ],
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? colors.primary : colors.outlineVariant,
            width: 2,
          ),
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 180),
                    height: 34,
                    width: 34,
                    decoration: BoxDecoration(
                      color: selected
                          ? colors.primary
                          : colors.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Center(
                      child: selected
                          ? Icon(
                              Icons.check_rounded,
                              size: 20,
                              color: colors.onPrimary,
                            )
                          : Text(
                              marker,
                              style: const TextStyle(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Text(
                      label,
                      style: const TextStyle(
                        fontSize: 16,
                        height: 1.35,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
