import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../l10n/app_localizations.dart';
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
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initialLoad();
    });
  }

  Future<void> _initialLoad() async {
    final storyProvider = context.read<StoryProvider>();

    await storyProvider.loadStories();

    if (!_initialSyncDone) {
      _initialSyncDone = true;
      await _syncAndRefresh();
    }
  }

  Future<void> _syncAndRefresh() async {
    final storyProvider = context.read<StoryProvider>();
    final syncProvider = context.read<SyncProvider>();
    final l10n = context.read<AppLocalizations>();

    final newCount = await syncProvider.syncNow();

    await storyProvider.loadStories();

    if (mounted && newCount < 0) {
      final err = syncProvider.lastSyncError;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            err != null
                ? l10n.t('home.syncError', args: {'message': err})
                : l10n.t('home.serverUnreachable'),
          ),
          duration: const Duration(seconds: 4),
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
      if (mounted) provider.refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<StoryProvider>();
    final l10n = context.watch<AppLocalizations>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Nunti Go'),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: l10n.t('home.settingsTooltip'),
            onPressed: _openSettings,
          ),
        ],
      ),
      body: _buildBody(provider, l10n),
    );
  }

  Widget _buildBody(StoryProvider provider, AppLocalizations l10n) {
    if (provider.isLoading && provider.stories.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

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
                label: Text(l10n.t('home.retry')),
              ),
            ],
          ),
        ),
      );
    }

    if (provider.stories.isEmpty) {
      return RefreshIndicator(
        onRefresh: _syncAndRefresh,
        child: LayoutBuilder(
          builder: (context, constraints) => SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: constraints.maxHeight),
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.article_outlined, size: 56, color: Colors.grey),
                      const SizedBox(height: 16),
                      Text(
                        l10n.t('home.empty'),
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.grey, fontSize: 15),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        l10n.t('home.emptyPull'),
                        style: const TextStyle(color: Colors.grey, fontSize: 12),
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