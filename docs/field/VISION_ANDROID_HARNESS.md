# Android field harness

The Kotlin application captures frames from the rear camera with CameraX. It
requires a realtime camera timestamp and selects the latest pending JPEG. The
desktop runs Guardian. The phone requests local English TTS, rejects expired
or superseded alerts and reports local utterance callbacks. Stop, backgrounding
and connection loss clear the active session.

See the [Android project instructions](../../apps/vision-field-android/README.md)
for the JDK, SDK, build commands and OneDrive build-directory setting. See the
[field guide](../releases/VISION_ALPHA_V1_FIELD_GUIDE.md) for pairing.

A local JVM test or desktop fixture cannot verify a physical camera or earbud.
During device evaluation record camera timestamp support, sensor availability,
transport type, worker status, chosen voice, audio route and callback timing.
Keep any independently measured acoustic onset separate from the callback.
