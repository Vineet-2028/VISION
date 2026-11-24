package dev.sentinel.field

import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.DataInputStream

class DiagnosticFramesTest {
    private fun frame(sequence: Long) = CameraFrame(sequence, sequence * 100_000_000L,
        sequence * 100_000_000L, 90, 640, 480, ByteArray(200_000), null)

    @Test fun recordingRequiresConsentAndRevocationClearsMemory() {
        val buffer = DiagnosticFrames()
        buffer.offer(frame(1))
        assertNull(buffer.snapshot("session"))
        buffer.enable(true)
        buffer.offer(frame(2))
        assertNotNull(buffer.snapshot("session"))
        buffer.enable(false)
        assertNull(buffer.snapshot("session"))
    }

    @Test fun snapshotPreservesAvailableFrameIdentityAndBounds() {
        val buffer = DiagnosticFrames()
        buffer.enable(true)
        for (i in 0L..99L) buffer.offer(frame(i))
        val bytes = buffer.snapshot("session")!!
        assertTrue(bytes.size < 4 * 1024 * 1024 + 4096)
        DataInputStream(ByteArrayInputStream(bytes)).use {
            assertEquals("VISION_DIAGNOSTIC_FRAMES_V1", it.readUTF())
            assertEquals("session", it.readUTF())
            it.readLong()
            val count = it.readInt()
            assertTrue(count in 1..24)
            val sequence = it.readLong()
            assertTrue(sequence >= 79)
            assertEquals(sequence * 100_000_000L, it.readLong())
            assertEquals(90, it.readInt())
            assertEquals(640, it.readInt())
            assertEquals(480, it.readInt())
        }
    }
}
