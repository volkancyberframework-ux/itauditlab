import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';
import 'api.dart';

class PersonalAddressSettings extends StatefulWidget {
  final Api api;
  final Map<String, dynamic> address;
  final ValueChanged<Map<String, dynamic>> onSaved;
  const PersonalAddressSettings({
    super.key,
    required this.api,
    required this.address,
    required this.onSaved,
  });
  @override
  State<PersonalAddressSettings> createState() =>
      _PersonalAddressSettingsState();
}

class _PersonalAddressSettingsState extends State<PersonalAddressSettings> {
  late final TextEditingController name;
  bool busy = false;
  String? error;
  @override
  void initState() {
    super.initState();
    name = TextEditingController(text: widget.address['slug'] as String? ?? '');
  }

  @override
  void dispose() {
    name.dispose();
    super.dispose();
  }

  Future<void> save({bool remove = false}) async {
    final slug = remove ? '' : name.text.trim().toLowerCase();
    if (!remove && !RegExp(r'^[a-z][a-z0-9-]{1,28}[a-z0-9]$').hasMatch(slug)) {
      setState(
        () => error =
            '3–30 karakter kullan. Harfle başla; a–z, rakam ve tire kullanabilirsin. Son karakter tire olamaz.',
      );
      return;
    }
    if ((widget.address['slug'] as String? ?? '').isNotEmpty &&
        slug != widget.address['slug']) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(
            remove ? 'Kişisel adresi kaldır?' : 'Kişisel adresi değiştir?',
          ),
          content: const Text(
            'Eski adres artık hesabına ait olmayacak ve başka biri seçebilecek. Kartların ve ilerlemen hesabında kalır.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Vazgeç'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Devam et'),
            ),
          ],
        ),
      );
      if (confirmed != true || !mounted) return;
    }
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final result = Map<String, dynamic>.from(
        await widget.api.request('profile/address/', body: {'slug': slug}),
      );
      if (!mounted) return;
      name.text = result['slug'] as String;
      widget.onSaved(result);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            remove ? 'Kişisel adres kaldırıldı.' : 'Kişisel adresin hazır.',
          ),
        ),
      );
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final url = widget.address['url'] as String? ?? '';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Kişisel web adresin',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            const Text(
              'Uygulamaya kendi adresinden gir: örneğin ayse.grcustasi.com. Aynı hesabınla giriş yaparak kartlarına, sorularına ve seslerine ulaşabilirsin.',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: name,
              enabled: !busy,
              autocorrect: false,
              enableSuggestions: false,
              textCapitalization: TextCapitalization.none,
              maxLength: 30,
              decoration: const InputDecoration(
                labelText: 'Adres adı',
                hintText: 'ayse',
                helperText: 'a–z, 0–9 ve tire • 3–30 karakter',
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) {
                if (!busy) save();
              },
            ),
            const Text('.grcustasi.com'),
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(
                  error!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: busy ? null : () => save(),
                  icon: busy
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.check),
                  label: const Text('Adresi kaydet'),
                ),
                if (url.isNotEmpty)
                  TextButton(
                    onPressed: busy ? null : () => save(remove: true),
                    child: const Text('Adresi kaldır'),
                  ),
              ],
            ),
            if (url.isNotEmpty) ...[
              const SizedBox(height: 16),
              SelectableText(url, style: Theme.of(context).textTheme.bodyLarge),
              Wrap(
                spacing: 8,
                children: [
                  TextButton.icon(
                    onPressed: () async {
                      await Clipboard.setData(ClipboardData(text: url));
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Adres kopyalandı.')),
                        );
                      }
                    },
                    icon: const Icon(Icons.copy),
                    label: const Text('Kopyala'),
                  ),
                  TextButton.icon(
                    onPressed: () async {
                      final opened = await launchUrl(
                        Uri.parse(url),
                        mode: LaunchMode.externalApplication,
                      );
                      if (!opened && context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Adres açılamadı. Kopyalayıp tarayıcıda açabilirsin.',
                            ),
                          ),
                        );
                      }
                    },
                    icon: const Icon(Icons.open_in_new),
                    label: const Text('Adresi aç'),
                  ),
                ],
              ),
              const Text(
                'Bu adres herkese açıktır. Hesap bilgilerin yalnızca giriş yaptıktan sonra görünür. Yeni adreste yeniden giriş yapman gerekebilir.',
              ),
            ],
          ],
        ),
      ),
    );
  }
}
