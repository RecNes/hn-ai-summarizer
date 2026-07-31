import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/story_provider.dart';
import '../providers/sync_provider.dart';
import '../widgets/story_card.dart';
import 'settings_screen.dart';
import 'story_detail_screen.dart';

/// Home screen showing the offline story list.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _initialSyncDone = false;

  @override
  void initState() {
    super.initState();
    // Load stories from local DB + pull new ones from server on first build
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initialLoad();
    });
  }

  /// First load: read local DB, then pull fresh data from server.
  Future<void> _initialLoad() async {
    final storyProvider = context.read<StoryProvider>();

    // Show local stories immediately (offline-first)
    await storyProvider.loadStories();

    // Pull new stories from server (if network available)
    if (!_initialSyncDone) {
      _initialSyncDone = true;
      await _syncAndRefresh();
    }
  }

  /// Pull from server, then reload local list.
  Future<void> _syncAndRefresh() async {
    final storyProvider = context.read<StoryProvider>();
    final syncProvider = context.read<SyncProvider>();

    // Fetch new stories from API → upsert into local DB
    final newCount = await syncProvider.syncNow();

    // Reload list from local DB (shows new + existing stories)
    await storyProvider.loadStories();

    // If sync failed, surface a brief message
    if (mounted && newCount < 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Sunucuya ulaşılamadı. Çevrimdışı makaleler gösteriliyor.'),
          duration: Duration(seconds: 3),
        ),
      );
    }
  }

  void _openSettings() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const SettingsScreen()),
    );
  }

  void _openStory(StoryProvider provider, int storyId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => StoryDetailScreen(storyId: storyId),
      ),
    ).then((_) {
      // Refresh on return (read status may have changed)
      if (mounted) provider.refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<StoryProvider>();

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.settings),
          tooltip: 'Ayarlar',
          onPressed: _openSettings,
        ),
        title: const Text('HNS Take Away'),
        centerTitle: false,
        actions: [
          // Refresh: pull new stories from server + reload list
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Senkronize Et',
            onPressed: provider.isLoading ? null : _syncAndRefresh,
          ),
        ],
      ),
      body: _buildBody(provider),
    );
  }

  Widget _buildBody(StoryProvider provider) {
    // Loading
    if (provider.isLoading && provider.stories.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    // Error with no data
    if (provider.error != null && provider.stories.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.grey[400]),
              const SizedBox(height: 12),
              Text(
                provider.error!,
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey[600]),
              ),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _syncAndRefresh,
                icon: const Icon(Icons.refresh),
                label: const Text('Tekrar Dene'),
              ),
            ],
          ),
        ),
      );
    }

    // Empty state
    if (provider.stories.isEmpty) {
      return RefreshIndicator(
        onRefresh: _syncAndRefresh,
        child: LayoutBuilder(
          builder: (context, constraints) => SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight),
              child: const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.article_outlined, size: 56, color: Colors.grey),
                      SizedBox(height: 16),
                      Text(
                        'Henüz makale yok.\nYukarıdaki senkronize et ikonu ile\nsunucudan çekebilirsiniz.',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey, fontSize: 15),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Aşağı çekerek de yenileyebilirsiniz.',
                        style: TextStyle(color: Colors.grey, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }

    // Story list
    return RefreshIndicator(
      onRefresh: _syncAndRefresh,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        itemCount: provider.stories.length,
        itemBuilder: (context, index) {
          final story = provider.stories[index];
          return StoryCard(
            story: story,
            onTap: () => _openStory(provider, story.id),
          );
        },
      ),
    );
  }
}