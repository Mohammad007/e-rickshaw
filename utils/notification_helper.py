"""Push notification helper (FCM).

Development stub: logs to console. In production, plug in the Firebase Admin SDK
or the FCM HTTP v1 API and send to the stored `fcm_token`.
"""


def send_push(fcm_token, title, body, data=None):
    """Send a push notification to a single device token."""
    if not fcm_token:
        return False

    # TODO: Replace with real FCM delivery, e.g.:
    # from firebase_admin import messaging
    # messaging.send(messaging.Message(
    #     token=fcm_token,
    #     notification=messaging.Notification(title=title, body=body),
    #     data={k: str(v) for k, v in (data or {}).items()},
    # ))
    print(f"🔔 PUSH -> {fcm_token[:12]}... | {title}: {body} | data={data or {}}")
    return True


def notify_driver_new_ride(fcm_token, booking_code, pickup_address, fare):
    return send_push(
        fcm_token,
        title="नई सवारी! 🛺",
        body=f"{pickup_address} | आप कमाएंगे Rs.{fare}",
        data={"type": "new_ride", "booking_code": booking_code},
    )


def notify_user_driver_accepted(fcm_token, driver_name, vehicle_number):
    return send_push(
        fcm_token,
        title="चालक आ रहा है 🛺",
        body=f"{driver_name} ({vehicle_number}) आपकी ओर आ रहे हैं",
        data={"type": "driver_accepted"},
    )
