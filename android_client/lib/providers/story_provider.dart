import 'package:flutter/foundation.dart';

import '../models/story.dart';
import '../services/database_service.dart';

/// Manages story list state and loads stories from local database.
class StoryProvider extends ChangeNotifier {
  final DatabaseService _databaseService;
  List<Story> _stories = [];
  bool _isLoading = false;
  String? _error;

  StoryProvider(this._databaseService);

  List<Story> get stories => _stories;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isEmpty => _stories.isEmpty && !_isLoading;

  /// Load all stories from the local SQLite database.
  Future<void> loadStories() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _stories = await _databaseService.getStories();
    } catch (e) {
      _error = 'Makaleler yüklenirken bir hata oluştu: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Refresh the story list from local DB.
  Future<void> refresh() => loadStories();

  /// Mark a story as read locally and update in-memory state.
  Future<void> markAsRead(Story story) async {
    if (story.isRead) return;

    await _databaseService.markStoriesAsRead([story.id]);

    // Update in-memory copy
    final index = _stories.indexWhere((s) => s.id == story.id);
    if (index != -1) {
      final updated = Story(
        id: story.id,
        hackerNewsId: story.hackerNewsId,
        title: story.title,
        titleTr: story.titleTr,
        url: story.url,
        score: story.score,
        author: story.author,
        contentTr: story.contentTr,
        commentsSummary: story.commentsSummary,
        imageUrl: story.imageUrl,
        isTranslated: story.isTranslated,
        isRead: true,
        isHighlighted: story.isHighlighted,
        isDimmed: story.isDimmed,
        createdAt: story.createdAt,
        hnCreatedAt: story.hnCreatedAt,
      );
      _stories[index] = updated;
      notifyListeners();
    }
  }

  /// Get a single story by id.
  Story? storyById(int id) {
    for (final s in _stories) {
      if (s.id == id) return s;
    }
    return null;
  }
}