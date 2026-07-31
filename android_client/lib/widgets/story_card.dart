import 'package:flutter/material.dart';

import '../models/story.dart';
import '../utils/date_formatter.dart';

/// Story card shown in the home screen list.
/// Shows title (translated if available), score, author, and relative date.
class StoryCard extends StatelessWidget {
  final Story story;
  final VoidCallback? onTap;

  const StoryCard({
    super.key,
    required this.story,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final textTheme = theme.textTheme;
    final title = story.titleTr ?? story.title;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Read indicator ────────────
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Icon(
                  Icons.circle,
                  size: 10,
                  color: story.isRead
                      ? (isDark ? Colors.grey[700] : Colors.grey[300])
                      : Theme.of(context).colorScheme.primary,
                ),
              ),
              const SizedBox(width: 12),

              // ── Content ───────────────────
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                      style: textTheme.bodyLarge?.copyWith(
                        fontWeight: story.isRead ? FontWeight.w400 : FontWeight.w600,
                        height: 1.3,
                      ),
                    ),
                    const SizedBox(height: 8),

                    // ── Meta row ─────────────
                    Row(
                      children: [
                        if (story.score != null) ...[
                          Icon(
                            Icons.arrow_upward,
                            size: 14,
                            color: isDark ? Colors.grey[400] : Colors.grey[600],
                          ),
                          const SizedBox(width: 2),
                          Text(
                            '${story.score}',
                            style: textTheme.bodySmall?.copyWith(
                              color: isDark ? Colors.grey[400] : Colors.grey[600],
                            ),
                          ),
                          const SizedBox(width: 10),
                        ],
                        if (story.author != null)
                          Flexible(
                            child: Text(
                              story.author!,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: textTheme.bodySmall?.copyWith(
                                color: isDark ? Colors.grey[400] : Colors.grey[600],
                              ),
                            ),
                          ),
                        const Spacer(),
                        Text(
                          DateFormatter.relative(story.createdAt),
                          style: textTheme.bodySmall?.copyWith(
                            color: isDark ? Colors.grey[500] : Colors.grey[500],
                          ),
                        ),
                      ],
                    ),

                    // ── Translation badge ────
                    if (story.isTranslated && story.titleTr != null) ...[
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.secondaryContainer,
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'TR',
                          style: textTheme.labelSmall?.copyWith(
                            fontWeight: FontWeight.bold,
                            color: Theme.of(context).colorScheme.onSecondaryContainer,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 8),

              // ── Chevron ───────────────────
              Icon(
                Icons.chevron_right,
                size: 18,
                color: isDark ? Colors.grey[600] : Colors.grey[400],
              ),
            ],
          ),
        ),
      ),
    );
  }
}