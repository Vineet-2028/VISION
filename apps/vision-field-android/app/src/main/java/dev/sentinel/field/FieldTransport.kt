package dev.sentinel.field

import android.os.SystemClock
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.nio.ByteBuffer
import java.util.UUID

/** Blocking transport: call only from the single transport executor, never CameraX/UI. */
class FieldTransport(address: String, private val token: String, private val fingerprint: String? = null, private val certificate: String? = null) {
    private val origin: URI = gatewayOrigin(address)
    private val pinnedFactory = fingerprint?.let { Pairing.socketFactory(it, checkNotNull(certificate)) }
    var sessionId: String? = null
        private set
    var sync: ClockSync? = null
        private set
    private var audioEnabled = false
    private var releaseId = "UNKNOWN"
    private val received = LinkedHashSet<String>()
    var acceptedFrames = 0L
        private set

    init {
        require(token.length >= 32)
        require(origin.userInfo == null && origin.query == null && origin.fragment == null)
        require(origin.path.isNullOrEmpty() || origin.path == "/")
        val loopback = origin.host == "127.0.0.1" || origin.host == "localhost"
        require(origin.scheme == "https" || (loopback && origin.scheme == "http")) { "LAN requires trusted HTTPS; USB reverse may use loopback HTTP" }
    }

    fun request(path: String, value: JSONObject? = null, bytes: ByteArray? = null): JSONObject {
        val connection = origin.resolve(path).toURL().openConnection() as HttpURLConnection
        if (pinnedFactory != null) {
            require(connection is javax.net.ssl.HttpsURLConnection)
            connection.sslSocketFactory = pinnedFactory
        }
        connection.connectTimeout = 1500
        connection.readTimeout = 1500
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("Authorization", "Bearer $token")
        connection.setRequestProperty("Accept", "application/json")
        try {
            val body = bytes ?: value?.toString()?.toByteArray(Charsets.UTF_8)
            if (body != null) {
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", if (bytes == null) "application/json" else "application/octet-stream")
                connection.setFixedLengthStreamingMode(body.size)
                connection.outputStream.use { it.write(body) }
            }
            check(connection.responseCode == 200) { "Gateway rejected request (${connection.responseCode})" }
            val response = connection.inputStream.use { input ->
                val buffer = java.io.ByteArrayOutputStream()
                val chunk = ByteArray(8192)
                while (true) {
                    val count = input.read(chunk)
                    if (count < 0) break
                    check(buffer.size() + count <= 1_048_576) { "Oversized response" }
                    buffer.write(chunk, 0, count)
                }
                buffer.toString("UTF-8")
            }
            return JSONObject(response)
        } finally { connection.disconnect() }
    }

    fun start(width: Int, height: Int, audio: Boolean) {
        check(sessionId == null)
        audioEnabled = audio
        val result = request("/v1/session", JSONObject().put("protocol_version", PROTOCOL)
            .put("client_version", "0.1.0").put("device_id", UUID.randomUUID().toString())
            .put("mode", "ANDROID_FIELD_HARNESS").put("width", width).put("height", height)
            .put("format", "JPEG").put("capabilities", org.json.JSONArray(listOf("CAMERA_REALTIME_CLOCK", if (audio) "TTS" else "NO_AUDIO"))))
        check(result.getString("protocol_version") == PROTOCOL)
        sessionId = result.getString("session_id")
        releaseId = result.getString("configuration_hash")
        sync = List(3) { synchronize(); checkNotNull(sync) }.minBy { it.rttNs }
    }

    fun synchronize() {
        val t0 = SystemClock.elapsedRealtimeNanos()
        val challenge = request("/v1/sync/start", JSONObject().put("session_id", sessionId).put("t0", t0.toString()))
        val t3 = SystemClock.elapsedRealtimeNanos()
        val result = request("/v1/sync/finish", JSONObject()
            .put("session_id", sessionId)
            .put("challenge", challenge.getString("challenge")).put("t3", t3.toString()))
        val estimate = ClockSync.estimate(t0, challenge.getString("t1").toLong(),
            challenge.getString("t2").toLong(), t3, result.getInt("version"))
        check(estimate.uncertainty(SystemClock.elapsedRealtimeNanos()) <= 100_000_000L) { "Clock synchronization too uncertain" }
        sync = estimate
    }

    fun send(frame: CameraFrame) {
        val clock = checkNotNull(sync)
        val now = SystemClock.elapsedRealtimeNanos()
        if (now - clock.measuredClientNs > 5_000_000_000L) synchronize()
        require(frame.jpeg.size <= 512_000)
        if (now - frame.cameraNs >= 500_000_000L) return
        val header = JSONObject().put("protocol_version", PROTOCOL).put("session_id", sessionId)
            .put("sequence", frame.sequence).put("camera_ns", frame.cameraNs.toString())
            .put("capture_ns", frame.captureNs.toString()).put("send_ns", SystemClock.elapsedRealtimeNanos().toString())
            .put("sync_version", checkNotNull(sync).version).put("rotation", frame.rotation)
            .put("width", frame.width).put("height", frame.height).put("format", "JPEG").put("jpeg_quality", 75)
            .put("sensors", frame.sensors)
            .toString().toByteArray(Charsets.UTF_8)
        val packet = ByteBuffer.allocate(4 + header.size + frame.jpeg.size).putInt(header.size).put(header).put(frame.jpeg).array()
        request("/v1/frame", bytes = packet)
        acceptedFrames++
    }

    fun close() {
        try { if (sessionId != null) request("/v1/close", JSONObject().put("session_id", sessionId)) }
        finally { sessionId = null; sync = null }
    }

    fun receive(speech: FieldSpeech, onReceive: (SpeechEvent) -> Unit): String {
        val status = request("/v1/alerts")
        check(status.optString("session_id") == sessionId && status.optString("status") == "CONNECTED") { "Session ended" }
        val alerts = if (audioEnabled) status.optJSONObject("result")?.optJSONArray("field_alerts") else null
        for (index in 0 until (alerts?.length() ?: 0)) {
            val item = checkNotNull(alerts).getJSONObject(index)
            val alertId = item.getString("alert_id")
            if (received.add(alertId)) {
                if (received.size > 128) received.remove(received.first())
                onReceive(SpeechEvent("PHONE_RESULT_RECEIVED", alertId, SystemClock.elapsedRealtimeNanos(), emptyList()))
            }
            speech.submit(FieldAlert(item.getString("session_id"), item.getString("alert_id"), item.getString("text"),
                item.getString("deadline_host_ns").toLong(), item.getString("source_host_ns").toLong(),
                item.getString("state_host_ns").toLong(),
                item.optJSONArray("reason_codes")?.let { reasons -> (0 until minOf(reasons.length(),16)).map { reasons.getString(it).take(100) } } ?: emptyList(),
                item.optString("semantic_level", "UNKNOWN").take(32), releaseId), checkNotNull(sync))
        }
        return status.optString("worker_status", "UNAVAILABLE")
    }

    fun speechEvent(event: SpeechEvent) {
        request("/v1/speech-event", JSONObject().put("session_id", sessionId)
            .put("kind", event.kind).put("alert_id", event.alertId).put("client_ns", event.clientNs.toString())
            .put("available_outputs", org.json.JSONArray(event.availableOutputs)))
    }
}

data class SpeechEvent(val kind: String, val alertId: String, val clientNs: Long, val availableOutputs: List<String>)

data class CameraFrame(val sequence: Long, val cameraNs: Long, val captureNs: Long,
    val rotation: Int, val width: Int, val height: Int, val jpeg: ByteArray, val sensors: JSONObject? = null)
