import 'dart:convert';
import 'dart:io';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_timezone/flutter_timezone.dart';
import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

class DailyNotifications {
  final plugin = FlutterLocalNotificationsPlugin();
  final storage = const FlutterSecureStorage();
  bool enabled = false;
  bool ready = false;
  bool syncing = false;
  Future<void>? initialization;
  String zone = 'Europe/Istanbul';
  Map<String, dynamic>? latestPlan;

  Future<String> timezoneName() async {
    if (Platform.isIOS || Platform.isAndroid) {
      try {
        zone = (await FlutterTimezone.getLocalTimezone()).identifier;
      } catch (_) {}
    }
    return zone;
  }

  Future<void> initialize() {
    if (!(Platform.isIOS || Platform.isAndroid)) return Future.value();
    return initialization ??= initializeOnce();
  }

  Future<void> initializeOnce() async {
    tzdata.initializeTimeZones();
    await timezoneName();
    tz.setLocalLocation(tz.getLocation(zone));
    await plugin.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(
          requestAlertPermission: false,
          requestBadgePermission: false,
          requestSoundPermission: false,
        ),
      ),
    );
    final stored = await storage.read(key: 'grc_daily_enabled');
    if (stored == null) {
      final granted = Platform.isIOS
          ? await plugin
                .resolvePlatformSpecificImplementation<
                  IOSFlutterLocalNotificationsPlugin
                >()
                ?.requestPermissions(alert: true, sound: true, badge: false)
          : await plugin
                .resolvePlatformSpecificImplementation<
                  AndroidFlutterLocalNotificationsPlugin
                >()
                ?.requestNotificationsPermission();
      enabled = granted == true;
      await storage.write(key: 'grc_daily_enabled', value: '$enabled');
    } else {
      enabled = stored == 'true';
    }
    ready = true;
  }

  Future<bool> setEnabled(bool value) async {
    await initialize();
    if (!ready) return false;
    if (value) {
      final granted = Platform.isIOS
          ? await plugin
                .resolvePlatformSpecificImplementation<
                  IOSFlutterLocalNotificationsPlugin
                >()
                ?.requestPermissions(alert: true, sound: true, badge: false)
          : await plugin
                .resolvePlatformSpecificImplementation<
                  AndroidFlutterLocalNotificationsPlugin
                >()
                ?.requestNotificationsPermission();
      value = granted == true;
    }
    enabled = value;
    await storage.write(key: 'grc_daily_enabled', value: '$value');
    if (!value) await plugin.cancelAllPendingNotifications();
    if (value && latestPlan != null) await sync(latestPlan!);
    return value;
  }

  Future<void> sync(Map<String, dynamic> plan) async {
    latestPlan = plan;
    await initialize();
    if (!ready || syncing) return;
    syncing = true;
    try {
      if (!enabled || plan['enabled'] != true) {
        await plugin.cancelAllPendingNotifications();
        return;
      }
      final now = tz.TZDateTime.now(tz.local);
      final previous =
          jsonDecode(await storage.read(key: 'grc_daily_planned_dates') ?? '{}')
              as Map<String, dynamic>;
      final next = <String, dynamic>{};
      final hour = (plan['hour'] as num?)?.toInt() ?? 19;
      // Preserve delivered-day guards across refresh, time changes and account switches.
      for (final entry in previous.entries) {
        if (DateTime.parse(
              entry.key,
            ).difference(DateTime(now.year, now.month, now.day)).inDays >=
            0) {
          next[entry.key] = entry.value;
        }
      }
      await plugin.cancelAllPendingNotifications();
      final unique = <String>{};
      for (final day in (plan['days'] as List? ?? []).take(60)) {
        if (!enabled || latestPlan == null) break;
        final date = day['date'] as String;
        if (!unique.add(date)) continue;
        final parsed = DateTime.parse(date);
        final when = tz.TZDateTime(
          tz.local,
          parsed.year,
          parsed.month,
          parsed.day,
          hour,
        );
        if (!when.isAfter(now)) continue;
        final old = previous[date];
        if (old is String && !DateTime.parse(old).isAfter(now)) continue;
        final id = parsed.year * 10000 + parsed.month * 100 + parsed.day;
        await plugin.zonedSchedule(
          id: id,
          title: day['title'],
          body: day['body'],
          scheduledDate: when,
          notificationDetails: const NotificationDetails(
            android: AndroidNotificationDetails(
              'grc_daily',
              'Günlük motivasyon',
              channelDescription: 'Günde en fazla bir öğrenme hatırlatması',
              importance: Importance.defaultImportance,
            ),
            iOS: DarwinNotificationDetails(presentBadge: false),
          ),
          androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        );
        next[date] = when.toIso8601String();
        // Persist each date before another refresh can reschedule a delivered day.
        await storage.write(
          key: 'grc_daily_planned_dates',
          value: jsonEncode(next),
        );
      }
    } finally {
      if (!enabled || latestPlan == null) {
        await plugin.cancelAllPendingNotifications();
      }
      syncing = false;
    }
  }

  Future<void> clearForLogout() async {
    latestPlan = null;
    await initialize();
    if (ready) await plugin.cancelAllPendingNotifications();
  }
}

final dailyNotifications = DailyNotifications();
