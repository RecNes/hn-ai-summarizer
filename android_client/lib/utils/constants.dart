/// Application-wide constants.
class AppConstants {
  AppConstants._();

  static const String appName = 'HNS Take Away';
  static const String packageName = 'com.hnstakeaway.app';
  static const String version = '0.0.0';

  // Pairing
  static const String mDnsServiceType = '_hnreader._tcp';
  static const Duration pairingCodeTimeout = Duration(minutes: 5);
  static const int pairingCodeLength = 6;
}

/// Sync status enum shared with sync provider.
enum SyncStatus { idle, syncing, connected, disconnected, error }