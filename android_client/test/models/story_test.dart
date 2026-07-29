import 'package:flutter_test/flutter_test.dart';
import 'package:hn_reader_client/models/story.dart';

void main() {
  group('Story', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 1,
        'hacker_news_id': '12345',
        'title': 'Test Story',
        'title_tr': 'Test Hikaye',
        'url': 'https://example.com',
        'score': 100,
        'author': 'author1',
        'content_tr': '- Point 1\n- Point 2',
        'comments_summary': 'Discussion summary',
        'image_url': null,
        'is_translated': true,
        'is_read': false,
        'is_highlighted': false,
        'is_dimmed': false,
        'created_at': '2026-01-01T00:00:00.000Z',
        'hn_created_at': null,
      };
      final story = Story.fromJson(json);
      expect(story.id, 1);
      expect(story.titleTr, 'Test Hikaye');
      expect(story.isTranslated, true);
      expect(story.isRead, false);
    });

    test('copyWith works', () {
      final story = Story(id: 1, hackerNewsId: '1', title: 'Test', createdAt: DateTime.now());
      final updated = story.copyWith(isRead: true, titleTr: 'Çeviri');
      expect(updated.isRead, true);
      expect(updated.titleTr, 'Çeviri');
      expect(updated.title, 'Test');
    });
  });
}