import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

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

    // Get from in-memory cache first
    Story? story = provider.storyById(widget.storyId);

    // Mark as read
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

    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!ok && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Bağlantı açılamadı')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        appBar: AppBar(title: const Text('Makale Detayı')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    final story = _story;
    if (story == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Makale Detayı')),
        body: const Center(child: Text('Makale bulunamadı')),
      );
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;
    final title = story.titleTr ?? story.title;
    final hasContent = story.contentTr != null && story.contentTr!.isNotEmpty;
    final hasCommentsSummary =
        story.commentsSummary != null && story.commentsSummary!.isNotEmpty;

    return Scaffold(
      appBar: AppBar(title: const Text('Makale Detayı')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Title ───────────────────────
            Text(
              title,
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w700,
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
                    text: '${story.score} puan',
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
                      color: Theme.of(context).colorScheme.secondaryContainer,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      'Türkçe Çeviri',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.onSecondaryContainer,
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
                title: 'İçerik',
              ),
              const SizedBox(height: 8),
              Text(
                story.contentTr!,
                style: TextStyle(
                  fontSize: 15,
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
                    'Bu içerik yapay zeka ile çevrilmiştir.',
                    style: TextStyle(
                      fontSize: 12,
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
                title: 'Yorum Analizi',
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
                  style: TextStyle(
                    fontSize: 14,
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
                  label: const Text('Orijinal Makaleyi Aç'),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                  ),
                ),
              ),
            const SizedBox(height: 24),

            // ── IDs (small footer) ──────────
            Center(
              child: Text(
                'HN #${story.hackerNewsId}',
                style: TextStyle(
                  fontSize: 11,
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
    final isDark = Theme.of(context).brightness == Brightness.dark;
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
          style: TextStyle(
            fontSize: 12,
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