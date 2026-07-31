/// Device pairing information.
class DeviceInfo {
  final String deviceId;
  final String deviceName;
  final String? authToken;
  final bool isPaired;
  final String? serverUrl;

  const DeviceInfo({
    required this.deviceId,
    required this.deviceName,
    this.authToken,
    this.isPaired = false,
    this.serverUrl,
  });

  factory DeviceInfo.fromMap(Map<String, dynamic> map) {
    return DeviceInfo(
      deviceId: map['device_id'] as String,
      deviceName: map['device_name'] as String? ?? 'Unknown Device',
      authToken: map['auth_token'] as String?,
      isPaired: map['is_paired'] as bool? ?? false,
      serverUrl: map['server_url'] as String?,
    );
  }
}