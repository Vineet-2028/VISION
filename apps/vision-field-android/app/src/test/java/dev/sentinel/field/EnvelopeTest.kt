package dev.sentinel.field

import javax.crypto.KeyGenerator
import org.junit.Assert.*
import org.junit.Test

class EnvelopeTest {
    @Test fun encryptionAuthenticatesPurposeAndDetectsTampering() {
        val key = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
        val aad = "history".toByteArray()
        val bytes = "private event".toByteArray()
        val a = Envelope.encrypt(key, bytes, aad)
        val b = Envelope.encrypt(key, bytes, aad)
        assertFalse(a.contentEquals(b))
        assertArrayEquals(bytes, Envelope.decrypt(key, a, aad))
        assertThrows(Exception::class.java) { Envelope.decrypt(key, a, "pairing".toByteArray()) }
        a[a.lastIndex] = (a.last().toInt() xor 1).toByte()
        assertThrows(Exception::class.java) { Envelope.decrypt(key, a, aad) }
    }
}
