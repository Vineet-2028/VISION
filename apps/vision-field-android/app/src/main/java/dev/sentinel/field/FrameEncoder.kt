package dev.sentinel.field

import android.graphics.Bitmap
import androidx.camera.core.ImageProxy
import java.io.ByteArrayOutputStream

/** Encodes a capture for transport. The caller owns and closes the ImageProxy. */
internal object FrameEncoder {
    private const val JPEG_QUALITY = 75
    private const val MAX_ENCODED_BYTES = 512_000

    fun encode(image: ImageProxy): ByteArray? {
        val bitmap = image.toBitmap()
        try {
            return ByteArrayOutputStream().use { output ->
                check(bitmap.compress(Bitmap.CompressFormat.JPEG, JPEG_QUALITY, output)) {
                    "Camera frame compression failed"
                }
                if (output.size() <= MAX_ENCODED_BYTES) output.toByteArray() else null
            }
        } finally {
            bitmap.recycle()
        }
    }
}
