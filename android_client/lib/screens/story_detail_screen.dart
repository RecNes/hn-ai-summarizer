import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../l10n/app_localizations.dart';
import '../models/story.dart';
import '../providers/story_provider.dart';
import '../utils/date_formatter.dart';

/// Story detail screen — full content, translation, summary, comments analysis.
class StoryDetailScreen extends StatefulWidget {
  final int storyId;

  const StoryDetailScreen({
    super.key,
    required this.storyId,
  });

  @override
  State<StoryDetailScreen> createState() => _StoryDetailScreenState();
}

class _StoryDetailScreenState extends State<StoryDetailScreen> {
  Story? _story;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final provider = context.read<StoryProvider>();

    Story? story = provider.storyById(widget.storyId);

    if (story != null && !story.isRead) {
      await provider.markAsRead(story);
      story = provider.storyById(widget.storyId);
    }

    if (mounted) {
      setState(() {
        _story = story;
        _loading = false;
      });
    }
  }

  Future<void> _openOriginal() async {
    final url = _story?.url;
    if (url == null) return;

    final uri = Uri.tryParse(url);
    if (uri == null) return;

    final l10n = context.read<AppLocalizations>();
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.t('detail.linkOpenFailed'))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.watch<AppLocalizations>();

    if (_loading) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.t('detail.title'))),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final story = _story;
    if (story == null) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.t('detail.title'))),
        body: Center(child: Text(l10n.t('detail.notFound'))),
      );
    }

    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final textTheme = theme.textTheme;
    final title = story.titleTr ?? story.title;
    final hasContent = story.contentTr != null && story.contentTr!.isNotEmpty;
    final hasCommentsSummary =
        story.commentsSummary != null && story.commentsSummary!.isNotEmpty;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.t('detail.title'))),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Title ───────────────────────
            Text(
              title,
              style: textTheme.headlineMedium?.copyWith(
                height: 1.3,
              ),
            ),
            const SizedBox(height: 12),

            // ── Meta row ────────────────────
            Wrap(
              spacing: 12,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                if (story.score != null)
                  _MetaChip(
                    icon: Icons.arrow_upward,
                    text: l10n.t('detail.points', args: {'count': story.score}),
                  ),
                if (story.author != null)
                  _MetaChip(
                    icon: Icons.person_outline,
                    text: story.author!,
                  ),
                _MetaChip(
                  icon: Icons.schedule,
                  text: DateFormatter.relative(story.createdAt),
                ),
                if (story.isTranslated && story.titleTr != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: theme.colorScheme.secondaryContainer,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      l10n.t('detail.translatedBadge'),
                      style: textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: theme.colorScheme.onSecondaryContainer,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 20),

            // ── Translated content ──────────
            if (hasContent) ...[
              _SectionHeader(
                icon: Icons.translate,
                title: l10n.t('detail.content'),
              ),
              const SizedBox(height: 8),
              Text(
                story.contentTr!,
                style: textTheme.bodyLarge?.copyWith(
                  height: 1.6,
                  color: isDark ? Colors.grey[300] : Colors.grey[800],
                ),
              ),
              const SizedBox(height: 24),

              if (story.isTranslated)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: isDark
                        ? Colors.grey[850]
                        : Colors.grey[100],
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    l10n.t('detail.aiTranslated'),
                    style: textTheme.bodySmall?.copyWith(
                      fontStyle: FontStyle.italic,
                      color: isDark ? Colors.grey[400] : Colors.grey[600],
                    ),
                  ),
                ),
              const SizedBox(height: 24),
            ],

            // ── Comments summary ────────────
            if (hasCommentsSummary) ...[
              _SectionHeader(
                icon: Icons.forum_outlined,
                title: l10n.t('detail.comments'),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: isDark ? Colors.grey[850] : Colors.grey[100],
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark ? Colors.grey[800]! : Colors.grey[300]!,
                  ),
                ),
                child: Text(
                  story.commentsSummary!,
                  style: textTheme.bodyMedium?.copyWith(
                    height: 1.5,
                    color: isDark ? Colors.grey[200] : Colors.grey[800],
                  ),
                ),
              ),
              const SizedBox(height: 24),
            ],

            // ── Original link ───────────────
            if (story.url != null)
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: _openOriginal,
                  icon: const Icon(Icons.open_in_new),
                  label: Text(l10n.t('detail.openOriginal')),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
            const SizedBox(height: 24),

            // ── IDs (small footer) ──────────
            Center(
              child: Text(
                'News #${story.hackerNewsId}',
                style: textTheme.labelSmall?.copyWith(
                  color: isDark ? Colors.grey[600] : Colors.grey[400],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Meta chip widget ────────────────────────

class _MetaChip extends StatelessWidget {
  final IconData icon;
  final String text;

  const _MetaChip({
    required this.icon,
    required this.text,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          icon,
          size: 14,
          color: isDark ? Colors.grey[400] : Colors.grey[600],
        ),
        const SizedBox(width: 4),
        Text(
          text,
          style: theme.textTheme.bodySmall?.copyWith(
            color: isDark ? Colors.grey[400] : Colors.grey[600],
          ),
        ),
      ],
    );
  }
}

// ── Section header widget ────────────────────

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;

  const _SectionHeader({
    required this.icon,
    required this.title,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    return Row(
      children: [
        Icon(
          icon,
          size: 18,
          color: theme.colorScheme.primary,
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: theme.textTheme.titleMedium?.copyWith(
            color: isDark ? Colors.grey[100] : Colors.grey[900],
          ),
        ),
      ],
    );
  }
}