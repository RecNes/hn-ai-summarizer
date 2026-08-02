/// Application-wide constants.
class AppConstants {
  AppConstants._();

  static const String appName = 'Nunti Go';
  static const String packageName = 'com.nontigo';
  static const String version = '0.0.0';

  // Pairing
  static const String mDnsServiceType = '_nunti._tcp';
  static const Duration pairingCodeTimeout = Duration(minutes: 5);
  static const int pairingCodeLength = 6;
}

/// Sync status enum shared with sync provider.
enum SyncStatus { idle, syncing, connected, disconnected, error }