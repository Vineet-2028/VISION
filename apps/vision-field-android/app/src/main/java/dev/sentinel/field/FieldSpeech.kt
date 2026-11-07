package dev.sentinel.field

import android.content.Context
import android.os.SystemClock
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** One replaceable utterance. System audio routing owns speaker/Bluetooth selection. */
class FieldSpeech(context: Context, private val spoken: (FieldAlert, Long) -> Unit = { _, _ -> }, private val event: (String, String, Long) -> Unit) : AutoCloseable {
    private val policy = AlertPolicy()
    private var engine: TextToSpeech? = null
    private var initialized = false
    private val initFinished = CountDownLatch(1)
    private var active: FieldAlert? = null
    private var clock: ClockSync? = null
    private var closed = false

    init {
        engine = TextToSpeech(context.applicationContext) { status ->
            synchronized(this) {
                if (!closed && status == TextToSpeech.SUCCESS) {
                    val local = engine?.voices?.filter { !it.isNetworkConnectionRequired && it.locale.language == Locale.ENGLISH.language }?.sortedBy { it.name }?.firstOrNull()
                    initialized = local != null && engine?.setVoice(local) == TextToSpeech.SUCCESS
                }
                initFinished.countDown()
            }
        }
        engine?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onBeginSynthesis(utteranceId: String, sampleRateInHz: Int, audioFormat: Int, channelCount: Int) {
                event("TTS_BEGIN_SYNTHESIS", utteranceId, SystemClock.elapsedRealtimeNanos())
            }
            override fun onStart(utteranceId: String) {
                if (utteranceId == "local-audio-test") return
                synchronized(this@FieldSpeech) {
                    val now = SystemClock.elapsedRealtimeNanos()
                    when (playbackStartDecision(active, utteranceId, clock, now)) {
                        PlaybackStartDecision.IGNORE_SUPERSEDED ->
                            event("TTS_CALLBACK_IGNORED_SUPERSEDED", utteranceId, now)
                        PlaybackStartDecision.REJECT_EXPIRED -> {
                            engine?.stop()
                            active = null
                            event("TTS_START_REJECTED_EXPIRED", utteranceId, now)
                        }
                        PlaybackStartDecision.START_ESTIMATE -> {
                            event("APP_TTS_PLAYBACK_START_ESTIMATE", utteranceId, now)
                            active?.let { spoken(it, checkNotNull(clock).latestHostNow(now) - it.sourceHostNs) }
                        }
                    }
                }
            }
            override fun onDone(utteranceId: String) = finished("TTS_COMPLETED", utteranceId)
            @Deprecated("Required by Android abstract listener")
            @Suppress("OVERRIDE_DEPRECATION")
            override fun onError(utteranceId: String) = finished("TTS_ERROR", utteranceId)
            @Deprecated("Android callback retained for supported API levels")
            override fun onStop(utteranceId: String, interrupted: Boolean) = finished("TTS_STOPPED", utteranceId)
        })
    }

    @Synchronized private fun finished(kind: String, id: String) {
        if (active?.alertId == id) active = null
        event(kind, id, SystemClock.elapsedRealtimeNanos())
    }

    @Synchronized fun available(): Boolean = initialized && !closed

    /** Only the transport executor waits for local voice discovery. */
    fun awaitLocalVoice(): Boolean {
        initFinished.await(1500, TimeUnit.MILLISECONDS)
        return available()
    }

    @Synchronized fun playAudioTest(message: String = "VISION audio test"): Boolean {
        require(message in setOf("VISION audio test", "VISION disconnected. Guardian unavailable.", "VISION camera unavailable."))
        return !closed && initialized && active == null &&
            engine?.speak(message, TextToSpeech.QUEUE_FLUSH, null, "local-audio-test") == TextToSpeech.SUCCESS
    }

    @Synchronized fun reset(session: String?) {
        active = null
        clock = null
        policy.reset(session)
        engine?.stop()
    }

    @Synchronized fun submit(alert: FieldAlert, sync: ClockSync): Boolean {
        val now = SystemClock.elapsedRealtimeNanos()
        if (closed || !initialized || !policy.accept(alert, sync, now)) return false
        clock = sync
        active = alert
        event("TTS_SUBMITTED", alert.alertId, now)
        val success = engine?.speak(alert.text, TextToSpeech.QUEUE_FLUSH, null, alert.alertId) == TextToSpeech.SUCCESS
        if (!success) { active = null; event("TTS_ERROR", alert.alertId, SystemClock.elapsedRealtimeNanos()) }
        return success
    }

    @Synchronized override fun close() {
        if (closed) return
        closed = true
        initFinished.countDown()
        reset(null)
        engine?.shutdown()
        engine = null
    }
}
