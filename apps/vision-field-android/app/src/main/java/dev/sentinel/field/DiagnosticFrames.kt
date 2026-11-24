package dev.sentinel.field

import android.content.Context
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.util.ArrayDeque

/** Explicitly enabled RAM buffer; snapshots contain only frames actually retained. */
internal class DiagnosticFrames {
    companion object {
        fun expire(context: Context) {
            val file = java.io.File(context.noBackupFilesDir, "diagnostic-clip.vault")
            val age = System.currentTimeMillis() - file.lastModified()
            if (file.exists() && (age < 0 || age >= 24 * 3600_000L)) {
                PrivateVault(context, "diagnostic-clip").clear()
            }
        }
    }
    private val frames = ArrayDeque<CameraFrame>()
    private var bytes = 0
    private var enabled = false

    @Synchronized fun enable(value: Boolean) {
        enabled = value
        frames.clear()
        bytes = 0
    }

    @Synchronized fun offer(frame: CameraFrame) {
        if (!enabled) return
        frames.addLast(frame)
        bytes += frame.jpeg.size
        while (frames.size > 24 || bytes > 4 * 1024 * 1024 ||
            (frames.isNotEmpty() && frame.cameraNs - frames.first.cameraNs > 2_000_000_000L)) {
            bytes -= frames.removeFirst().jpeg.size
        }
    }

    @Synchronized fun snapshot(sessionId: String, selectedSequence: Long? = null): ByteArray? {
        if (!enabled || frames.isEmpty()) return null
        val selected = if (selectedSequence == null) frames.last else frames.find { it.sequence == selectedSequence } ?: return null
        val retained = frames.filter { it.sequence <= selected.sequence && selected.cameraNs - it.cameraNs <= 2_000_000_000L }
        return ByteArrayOutputStream().use { bytes ->
            DataOutputStream(bytes).use { output ->
                output.writeUTF("VISION_DIAGNOSTIC_FRAMES_V1")
                output.writeUTF(sessionId)
                output.writeLong(System.currentTimeMillis())
                output.writeInt(retained.size)
                retained.forEach { frame ->
                    output.writeLong(frame.sequence)
                    output.writeLong(frame.cameraNs)
                    output.writeInt(frame.rotation)
                    output.writeInt(frame.width)
                    output.writeInt(frame.height)
                    output.writeInt(frame.jpeg.size)
                    output.write(frame.jpeg)
                }
            }
            bytes.toByteArray()
        }
    }
}
