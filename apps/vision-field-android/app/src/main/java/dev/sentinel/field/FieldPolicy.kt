package dev.sentinel.field

import java.util.concurrent.atomic.AtomicReference

const val PROTOCOL = "VISION_FIELD_PROTOCOL_V1"

fun gatewayOrigin(address: String): java.net.URI {
    val origin = java.net.URI(address)
    require(origin.userInfo == null && origin.query == null && origin.fragment == null)
    require(origin.path.isNullOrEmpty() || origin.path == "/")
    val hostParts = origin.host?.split(".") ?: emptyList()
    val parts = hostParts.mapNotNull { it.toIntOrNull() }
    val numeric = hostParts.size == 4 && parts.size == 4 && parts.all { it in 0..255 }
    val loopback = origin.host == "localhost" || (numeric && parts[0] == 127)
    val privateIp = numeric && (parts[0] == 10 || (parts[0] == 192 && parts[1] == 168) || (parts[0] == 172 && parts[1] in 16..31))
    require(loopback || privateIp) { "Only loopback and private LAN origins are supported" }
    require(origin.scheme == "https" || (loopback && origin.scheme == "http")) { "LAN requires HTTPS" }
    return origin
}

data class ClockSync(val offsetNs: Long, val uncertaintyNs: Long, val measuredClientNs: Long, val version: Int, val rttNs: Long) {
    fun uncertainty(now: Long): Long {
        require(now >= measuredClientNs && now - measuredClientNs <= 15_000_000_000L) { "Clock sync expired" }
        return uncertaintyNs + (now - measuredClientNs) / 1000L
    }
    fun latestHostNow(now: Long): Long = Math.addExact(Math.addExact(now, offsetNs), uncertainty(now))
    companion object {
        fun estimate(t0: Long, t1: Long, t2: Long, t3: Long, version: Int): ClockSync {
            require(t0 >= 0 && t1 >= 0 && t2 >= t1 && t3 >= t0 && version > 0)
            val rtt = Math.subtractExact(t3 - t0, t2 - t1)
            require(rtt in 0..2_000_000_000L)
            val offset = Math.floorDiv(Math.addExact(t1 - t0, t2 - t3), 2L)
            return ClockSync(offset, (rtt + 1) / 2, t3, version, rtt)
        }
    }
}

class LatestFrame<T> {
    private val pending = AtomicReference<T?>(null)
    fun offer(value: T): Boolean = pending.getAndSet(value) != null
    fun take(): T? = pending.getAndSet(null)
    fun clear() { pending.set(null) }
}

data class FieldAlert(val sessionId: String, val alertId: String, val text: String, val deadlineHostNs: Long, val sourceHostNs: Long, val stateHostNs: Long, val reasonCodes: List<String> = emptyList(), val semanticLevel: String = "UNKNOWN", val releaseId: String = "UNKNOWN")

enum class PlaybackStartDecision { IGNORE_SUPERSEDED, REJECT_EXPIRED, START_ESTIMATE }

fun playbackStartDecision(active: FieldAlert?, callbackId: String, sync: ClockSync?, now: Long): PlaybackStartDecision {
    if (active == null || active.alertId != callbackId) return PlaybackStartDecision.IGNORE_SUPERSEDED
    val fresh = try {
        sync != null && sync.uncertainty(now) <= 100_000_000L && sync.latestHostNow(now) < active.deadlineHostNs
    } catch (_: RuntimeException) { false }
    return if (fresh) PlaybackStartDecision.START_ESTIMATE else PlaybackStartDecision.REJECT_EXPIRED
}

/** One speech slot, with a watermark protecting against replay after ID eviction. */
class AlertPolicy {
    private var session: String? = null
    private var watermark = -1L
    private val ids = LinkedHashSet<String>()
    @Synchronized fun reset(sessionId: String?) { session = sessionId; watermark = -1; ids.clear() }
    @Synchronized fun accept(alert: FieldAlert, sync: ClockSync?, now: Long): Boolean {
        if (sync == null || alert.sessionId != session || alert.text.isBlank() || alert.text.length > 64 || alert.stateHostNs <= watermark || alert.alertId in ids) return false
        val current = try { if (sync.uncertainty(now)>100_000_000L) return false; sync.latestHostNow(now) } catch (_: IllegalArgumentException) { return false } catch (_: ArithmeticException) { return false }
        if (current >= alert.deadlineHostNs || alert.sourceHostNs < 0 || alert.sourceHostNs > current || alert.stateHostNs < alert.sourceHostNs || alert.stateHostNs > current) return false
        // A malformed desktop response must never extend the frozen 500 ms budget.
        if (alert.deadlineHostNs <= alert.sourceHostNs || alert.deadlineHostNs - alert.sourceHostNs > 500_000_000L) return false
        ids.add(alert.alertId); watermark = alert.stateHostNs
        if (ids.size > 128) ids.remove(ids.first())
        return true
    }
}
