import 'package:flutter/material.dart';

class AppColors {
  static const primary = Color(0xFF123653);
  static const ink = Color(0xFF132B40);
  static const background = Color(0xFFF5F7FA);
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
    ),
    scaffoldBackgroundColor: brightness == Brightness.light
        ? AppColors.background
        : const Color(0xFF101C1A),
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      backgroundColor: Colors.transparent,
      elevation: 0,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: BorderSide.none,
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(54),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      ),
    ),
  );
}

class PrimaryButton extends StatelessWidget {
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
  Widget build(BuildContext context) => FilledButton(
    onPressed: busy ? null : onPressed,
    child: AnimatedSwitcher(
      duration: const Duration(milliseconds: 200),
      child: busy
          ? const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : Text(label),
    ),
  );
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
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: selected ? colors.primary : colors.outlineVariant,
            width: selected ? 2 : 1,
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
