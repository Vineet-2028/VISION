package dev.sentinel.field

import org.junit.Assert.*
import org.junit.Test

class FieldPolicyTest {
    @Test fun localTransportRejectsPublicOriginsAndCleartextLan() {
        assertEquals("127.0.0.1", gatewayOrigin("http://127.0.0.1:8765").host)
        assertEquals("192.168.1.2", gatewayOrigin("https://192.168.1.2:8765").host)
        for (value in listOf("https://example.com", "http://192.168.1.2", "http://localhost/path", "http://user:pass@localhost", "http://127.attacker.0.0.1", "https://192.168.attacker.1.2")) {
            try { gatewayOrigin(value); fail("Accepted $value") } catch (_: IllegalArgumentException) { }
        }
    }
    @Test fun remoteDeadlineCannotExtendFrozenFreshness() {
        val policy = AlertPolicy(); policy.reset("s")
        assertFalse(policy.accept(FieldAlert("s","a","Object.",600_000_001,0,1000),ClockSync(0,0,1000,1,0),1100))
    }
    @Test fun clockOffsetAndUncertainty() {
        val sync = ClockSync.estimate(1000,1110,1120,1030,1)
        assertEquals(100L,sync.offsetNs); assertEquals(20L,sync.rttNs); assertEquals(10L,sync.uncertaintyNs)
    }
    @Test fun newestFrameReplacesPending() {
        val slot = LatestFrame<Int>(); assertFalse(slot.offer(1)); assertTrue(slot.offer(2)); assertEquals(2,slot.take()); assertNull(slot.take())
    }
    @Test fun expiredAndDuplicateAlertsNeverAccepted() {
        val policy = AlertPolicy();policy.reset("test");val sync = ClockSync(0,10,1000,1,20)
        val alert = FieldAlert("test","a","Object.",2000,900,1000)
        assertTrue(policy.accept(alert,sync,1100)); assertFalse(policy.accept(alert,sync,1101))
        assertFalse(policy.accept(alert.copy(alertId="b",stateHostNs=1001),sync,2000))
    }
    @Test fun disconnectAndSessionResetRejectOldMessages() {
        val policy=AlertPolicy();policy.reset("new")
        assertFalse(policy.accept(FieldAlert("old","a","Object.",3000,900,1000),ClockSync(0,0,1000,1,0),1100))
        policy.reset(null);assertFalse(policy.accept(FieldAlert("new","a","Object.",3000,900,1000),ClockSync(0,0,1000,1,0),1100))
    }
    @Test fun uncertainOrExpiredSyncCannotAuthorizeSpeech() {
        for(delay in listOf(50,100,250,500,1000)) {
            val policy=AlertPolicy();policy.reset("s")
            val ns=delay*1_000_000L
            val sync=ClockSync.estimate(1_000_000_000,1_000_000_000+ns,1_000_000_000+ns,1_000_000_000+2*ns,1)
            val source=sync.measuredClientNs+sync.offsetNs-1_000_000
            val alert=FieldAlert("s","a","Object.",source+500_000_000,source,source)
            assertEquals(delay<=100,policy.accept(alert,sync,sync.measuredClientNs))
        }
        val policy=AlertPolicy();policy.reset("s")
        val alert=FieldAlert("s","a","Object.",20_100_000_000,19_900_000_000,19_900_000_000)
        assertFalse(policy.accept(alert,ClockSync(0,0,1000,1,0),20_000_000_000))
        assertTrue(policy.accept(alert,ClockSync(0,0,20_000_000_000,1,0),20_000_000_000))
    }
    @Test fun supersededStartCallbackCannotStopCurrentSpeech() {
        val active=FieldAlert("s","new","Object.",2000,900,1000)
        val sync=ClockSync(0,0,1000,1,0)
        assertEquals(PlaybackStartDecision.IGNORE_SUPERSEDED,playbackStartDecision(active,"old",sync,1500))
        assertEquals(PlaybackStartDecision.START_ESTIMATE,playbackStartDecision(active,"new",sync,1500))
        assertEquals(PlaybackStartDecision.REJECT_EXPIRED,playbackStartDecision(active,"new",sync,2000))
        assertEquals(PlaybackStartDecision.IGNORE_SUPERSEDED,playbackStartDecision(null,"old",sync,1500))
    }
}
