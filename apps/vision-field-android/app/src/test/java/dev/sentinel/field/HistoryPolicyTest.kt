package dev.sentinel.field
import org.junit.Assert.*
import org.junit.Test
class HistoryPolicyTest {
    @Test fun retentionIsBoundedAndOverflowCannotExtendIt() {
        assertEquals(86_400_001L, HistoryPolicy.expires(1, 1))
        assertThrows(IllegalArgumentException::class.java) { HistoryPolicy.expires(1, 365) }
        assertThrows(ArithmeticException::class.java) { HistoryPolicy.expires(Long.MAX_VALUE, 30) }
        assertEquals(1000, HistoryPolicy.MAX_ROWS)
    }
}
