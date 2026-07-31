import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/settings_provider.dart';
import '../providers/sync_provider.dart';

/// Settings screen — theme, language, font size, connection management.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(title: const Text('Ayarlar')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── Theme ────────────────────────
          _SectionTitle(
            icon: Icons.palette_outlined,
            title: 'Tema',
          ),
          const SizedBox(height: 8),
          SegmentedButton<ThemeMode>(
            segments: const [
              ButtonSegment(
                value: ThemeMode.system,
                label: Text('Sistem'),
                icon: Icon(Icons.brightness_auto),
              ),
              ButtonSegment(
                value: ThemeMode.light,
                label: Text('Açık'),
                icon: Icon(Icons.light_mode),
              ),
              ButtonSegment(
                value: ThemeMode.dark,
                label: Text('Koyu'),
                icon: Icon(Icons.dark_mode),
              ),
            ],
            selected: {settings.themeMode},
            onSelectionChanged: (selection) {
              settings.setThemeMode(selection.first);
            },
          ),
          const SizedBox(height: 24),

          // ── Language ─────────────────────
          _SectionTitle(
            icon: Icons.language,
            title: 'Dil',
          ),
          const SizedBox(height: 8),
          Card(
            child: RadioGroup<String>(
              groupValue: settings.uiLanguage,
              onChanged: (v) {
                if (v != null) settings.setUiLanguage(v);
              },
              child: const Column(
                children: [
                  RadioListTile<String>(
                    title: Text('English'),
                    value: 'en',
                  ),
                  RadioListTile<String>(
                    title: Text('Türkçe'),
                    value: 'tr',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),

          // ── Font size ────────────────────
          _SectionTitle(
            icon: Icons.format_size,
            title: 'Yazı Boyutu',
          ),
          Row(
            children: [
              const Icon(Icons.text_fields, size: 16, color: Colors.grey),
              Expanded(
                child: Slider(
                  min: 13,
                  max: 22,
                  divisions: 9,
                  label: '${settings.fontSize.round()}',
                  value: settings.fontSize,
                  onChanged: (v) => settings.setFontSize(v),
                ),
              ),
              const Icon(Icons.text_fields, size: 24, color: Colors.grey),
            ],
          ),

          // Preview of font size
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(
              'Önizleme: ${settings.fontSize.round()} pt',
              style: TextStyle(fontSize: settings.fontSize),
            ),
          ),
          const SizedBox(height: 24),

          // ── Connection ───────────────────
          _SectionTitle(
            icon: Icons.link,
            title: 'Bağlantı',
          ),
          const SizedBox(height: 8),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: Icon(Icons.dns, color: isDark ? Colors.grey[400] : Colors.grey[600]),
                  title: const Text('Sunucu'),
                  subtitle: const Text('Bağlı cihaz'),
                  trailing: const Icon(Icons.check_circle, color: Colors.green, size: 20),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: Icon(Icons.link_off, color: isDark ? Colors.grey[400] : Colors.grey[600]),
                  title: const Text('Yeniden Eşleştir'),
                  subtitle: const Text('Mevcut eşleşmeyi kaldır'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => _confirmRePair(context),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),

          // ── App info ─────────────────────
          Center(
            child: Text(
              'HNS Take Away',
              style: TextStyle(
                fontSize: 13,
                color: isDark ? Colors.grey[600] : Colors.grey[400],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _confirmRePair(BuildContext context) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Yeniden Eşleştir'),
        content: const Text(
          'Mevcut eşleşme kaldırılacak ve yeni bir cihaz eşleştirme işlemi başlayacak. '
          'Devam etmek istiyor musunuz?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Vazgeç'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Eşleştirmeyi Kaldır'),
          ),
        ],
      ),
    );

    if (confirmed != true || !context.mounted) return;

    // Clear pairing data (disconnects WS too) and go back to pairing screen
    await context.read<SyncProvider>().clearPairing();

    if (context.mounted) {
      Navigator.popUntil(context, (route) => route.isFirst);
    }
  }
}

// ── Section title widget ────────────────────

class _SectionTitle extends StatelessWidget {
  final IconData icon;
  final String title;

  const _SectionTitle({
    required this.icon,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Row(
      children: [
        Icon(
          icon,
          size: 18,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
            color: isDark ? Colors.grey[100] : Colors.grey[900],
          ),
        ),
      ],
    );
  }
}