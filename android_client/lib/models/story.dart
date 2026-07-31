/// Story model for local storage and display.
class Story {
  final int id;
  final String hackerNewsId;
  final String title;
  final String? titleTr;
  final String? url;
  final int? score;
  final String? author;
  final String? contentTr;
  final String? commentsSummary;
  final String? imageUrl;
  final bool isTranslated;
  final bool isRead;
  final bool isHighlighted;
  final bool isDimmed;
  final DateTime createdAt;
  final DateTime? hnCreatedAt;

  const Story({
    required this.id,
    required this.hackerNewsId,
    required this.title,
    this.titleTr,
    this.url,
    this.score,
    this.author,
    this.contentTr,
    this.commentsSummary,
    this.imageUrl,
    this.isTranslated = false,
    this.isRead = false,
    this.isHighlighted = false,
    this.isDimmed = false,
    required this.createdAt,
    this.hnCreatedAt,
  });

  factory Story.fromMap(Map<String, dynamic> map) {
    return Story(
      id: map['id'] as int,
      hackerNewsId: map['hacker_news_id'] as String,
      title: map['title'] as String,
      titleTr: map['title_tr'] as String?,
      url: map['url'] as String?,
      score: map['score'] as int?,
      author: map['author'] as String?,
      contentTr: map['content_tr'] as String?,
      commentsSummary: map['comments_summary'] as String?,
      imageUrl: map['image_url'] as String?,
      isTranslated: (map['is_translated'] as int?) == 1,
      isRead: (map['is_read'] as int?) == 1,
      isHighlighted: (map['is_highlighted'] as int?) == 1,
      isDimmed: (map['is_dimmed'] as int?) == 1,
      createdAt: DateTime.parse(map['created_at'] as String),
      hnCreatedAt: map['hn_created_at'] != null
          ? DateTime.parse(map['hn_created_at'] as String)
          : null,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'hacker_news_id': hackerNewsId,
      'title': title,
      'title_tr': titleTr,
      'url': url,
      'score': score,
      'author': author,
      'content_tr': contentTr,
      'comments_summary': commentsSummary,
      'image_url': imageUrl,
      'is_translated': isTranslated ? 1 : 0,
      'is_read': isRead ? 1 : 0,
      'is_highlighted': isHighlighted ? 1 : 0,
      'is_dimmed': isDimmed ? 1 : 0,
      'created_at': createdAt.toIso8601String(),
      'hn_created_at': hnCreatedAt?.toIso8601String(),
    };
  }
}