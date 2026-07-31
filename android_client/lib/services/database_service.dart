import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

import '../models/story.dart';

/// Local SQLite database service for offline story storage.
class DatabaseService {
  Database? _db;

  Future<void> initialize() async {
    final dbPath = await getDatabasesPath();
    _db = await openDatabase(
      join(dbPath, 'hns_takeaway.db'),
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE stories (
            id INTEGER PRIMARY KEY,
            hacker_news_id TEXT NOT NULL,
            title TEXT NOT NULL,
            title_tr TEXT,
            url TEXT,
            score INTEGER,
            author TEXT,
            content_tr TEXT,
            comments_summary TEXT,
            image_url TEXT,
            is_translated INTEGER DEFAULT 0,
            is_read INTEGER DEFAULT 0,
            is_highlighted INTEGER DEFAULT 0,
            is_dimmed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            hn_created_at TEXT
          )
        ''');
      },
    );
  }

  /// Insert a batch of stories (upsert by primary key).
  Future<void> upsertStories(List<Story> stories) async {
    final db = _db;
    if (db == null) return;

    final batch = db.batch();
    for (final story in stories) {
      batch.insert(
        'stories',
        story.toMap(),
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }
    await batch.commit(noResult: true);
  }

  /// Fetch all stories, newest first.
  Future<List<Story>> getStories() async {
    final db = _db;
    if (db == null) return [];

    final rows = await db.query(
      'stories',
      orderBy: 'created_at DESC',
    );
    return rows.map(Story.fromMap).toList();
  }

  /// Fetch a single story by local id.
  Future<Story?> getStoryById(int id) async {
    final db = _db;
    if (db == null) return null;

    final rows = await db.query(
      'stories',
      where: 'id = ?',
      whereArgs: [id],
      limit: 1,
    );
    if (rows.isEmpty) return null;
    return Story.fromMap(rows.first);
  }

  /// Mark stories as read.
  Future<void> markStoriesAsRead(List<int> ids) async {
    final db = _db;
    if (db == null || ids.isEmpty) return;

    await db.update(
      'stories',
      {'is_read': 1},
      where: 'id IN (${List.filled(ids.length, '?').join(',')})',
      whereArgs: ids,
    );
  }

  /// Get the highest local story id (for incremental sync).
  Future<int> getLastStoryId() async {
    final db = _db;
    if (db == null) return 0;

    final result = await db.rawQuery('SELECT MAX(id) as max_id FROM stories');
    return (result.first['max_id'] as int?) ?? 0;
  }

  /// Clear all stories (factory reset / re-sync).
  Future<void> clearStories() async {
    final db = _db;
    if (db == null) return;
    await db.delete('stories');
  }
}